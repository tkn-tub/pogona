# Pogona
# Copyright (C) 2020 Data Communications and Networking (TKN), TU Berlin
#
# This file is part of Pogona.
#
# Pogona is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pogona is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pogona.  If not, see <https://www.gnu.org/licenses/>.


import logging
import coloredlogs
import argparse
import sys
import inspect
import os
import typing
import ruamel.yaml
import subprocess
import datetime

# Ignore flake8 "imported but unused" by adding `# noqa: F401`:

from . import util  # noqa: F401

# Enums:
from .integration import Integration  # noqa: F401
from .interpolation import Interpolation  # noqa: F401
from .geometry import Geometry, Shapes  # noqa: F401

from . import properties  # noqa: F401
from .component import Component, InitStages, NotificationStages  # noqa: F401

from .simulation_kernel import SimulationKernel  # noqa: F401
from .molecule_manager import MoleculeManager  # noqa: F401
from .vector_field import VectorField  # noqa: F401
from .vector_field_manager import VectorFieldManager  # noqa: F401
from .vector_field_parser import (  # noqa: F401
    VectorFieldParser,
    DummyBoundaryPointsVariant,
)
from .sensor import Sensor  # noqa: F401
from .sensor_manager import (  # noqa: F401
    SensorManager,
    SensorSubscriptionsUsage,
)
from .scene_manager import SceneManager  # noqa: F401
from .movement_predictor import MovementPredictor  # noqa: F401
from .movement_predictor import EmbeddedRungeKuttaMethod  # noqa: F401
from .movement_predictor import RKFehlberg45  # noqa: F401
from .mesh_manager import MeshManager  # noqa: F401
from .transformation import Transformation  # noqa: F401
from .molecule import Molecule  # noqa: F401
from .object import Object  # noqa: F401
from .injector import Injector  # noqa: F401
from .spray_nozzle import SprayNozzle  # noqa: F401
from .modulation import Modulation  # noqa: F401
from .modulation_ook import ModulationOOK  # noqa: F401
from .modulation_ppm import ModulationPPM  # noqa: F401
from .bitstream_generator import BitstreamGenerator  # noqa: F401
from .plotter_terminal import PlotterTerminal  # noqa: F401
from .plotter_csv import PlotterCSV  # noqa: F401
from .sensor_counting import SensorCounting  # noqa: F401
from .sensor_destructing import SensorDestructing  # noqa: F401
from .sensor_empirical import (  # noqa: F401
    SensorEmpirical,
    KnownSensors
)
from .sensor_empirical_radial_test import (  # noqa: F401
    SensorEmpiricalRadialTest
)
from .sensor_flow_rate import SensorFlowRate  # noqa: F401
from .sensor_teleporting import SensorTeleporting  # noqa: F401
from .config_preprocessing import (  # noqa: F401
    assemble_config_recursively,
    update_dict_recursively,
    write_config,
)
from .face import Face  # noqa: F401

import pogona.objects as objects  # noqa: F401


name = "pogona"

LOG = logging.getLogger(__name__)


def start_cli():
    """
    Start a simulation from the command line.
    This will be called if run as `python -m pogona ARGS…`.

    :return:
    """
    args = parse_args()
    setup_logging(
        verbosity=args.verbosity,
        log_file=args.log_file,
        log_file_verbosity=args.log_file_verbosity,
        results_dir=args.results_dir
    )
    if args.debug:
        import pdb
        pdb.set_trace()
    if args.param is None:
        args.param = []
    override_params = args_config_params_to_dict(args.param)
    try:
        simulation_kernel, components = SceneManager.construct_from_config(
            filename=args.config,
            openfoam_cases_path=args.openfoam_cases_path,
            additional_component_classes=dict(
                inspect.getmembers(objects, inspect.isclass)),
            results_dir=args.results_dir,
            override_config=override_params,
            log_config=args.log_config,
        )
        if not args.no_versions_file:
            write_versions_file(
                filename=os.path.join(args.results_dir, 'versions.txt'),
                openfoam_cases_path=args.openfoam_cases_path,
            )
        if args.profile_tool == "NONE":
            simulation_kernel.start()
        else:
            if args.profile_tool == "CPROFILE":
                import cProfile as profile
            else:
                import profile as profile
            pr = profile.Profile()
            pr.enable()
            simulation_kernel.start()
            pr.disable()
            profile_path = os.path.join(args.results_dir, args.profile_file)
            pr.dump_stats(profile_path)
        if not args.no_success_file:
            # Write a file called SUCCESS for Make, Snakemake, etc.:
            with open(os.path.join(args.results_dir, 'SUCCESS'), 'w') as f:
                f.write(datetime.datetime.now().isoformat())
    except BaseException as e:
        # Write stacktrace to log file (and stdout/stderr(?)):
        LOG.exception("Unhandled exception in simulation.")
        # Re-raise the exception so it can be caught by PDB, for example:
        raise e


def parse_args(existing_parser: argparse.ArgumentParser = None):
    """
    Parse command line arguments.

    :param existing_parser: Optional existing argument parser with custom
        arguments.
    :return:
    """
    if existing_parser is not None:
        existing_parser.add_help = False  # necessary for use as parent

    main_parser = argparse.ArgumentParser(
        prog="pogona",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[existing_parser] if existing_parser is not None else []
    )
    main_parser.add_argument(
        '--debug',
        action='store_true',
        help="Run the simulation with pdb or pdbpp for debugging."
    )

    group = main_parser.add_argument_group("Simulation")
    group.add_argument(
        '--openfoam-cases-path',
        '-o',
        required=True,
        help="Path to OpenFOAM cases (should include a `tube/` "
             "subdirectory)"
    )
    group.add_argument(
        '--config',
        help="Simulation configuration file, usually named `*.config.yaml`.",
        default="config.yaml"
    )
    group.add_argument(
        '--results-dir',
        help="Directory for result files. "
             "Paths for sensor logs, for example, that are defined in the "
             "configuration file will be relative to this path. "
             "Ignored if left as an empty string.",
        default='',
    )
    group.add_argument(
        '--param',
        '-p',
        nargs='*',
        help="Parameters to override from the configuration file. "
             "Example: "
             "`-p \"components.injector.injection_amount=42\" seed=2`."
    )

    group = main_parser.add_argument_group("Logging")
    group.add_argument(
        '--verbosity',
        help="Logging verbosity",
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    )
    group.add_argument(
        '--log-file',
        help="Name of the log file, relative to --results-dir.",
        default='simulation.log',
    )
    group.add_argument(
        '--no-success-file',
        action='store_true',
        help="Do not write a SUCCESS file. "
             "By default, a mostly empty file called SUCCESS will be written "
             "into --results-dir if the simulation finishes without errors. "
             "Such a file can be useful for tools such as GNU Make or "
             "Snakemake. "
             "For now, the date and time of when the simulation ended are the "
             "only content of the file."
    )
    group.add_argument(
        '--no-versions-file',
        action='store_true',
        help="Do not write a versions.txt file. "
             "With the purpose of making simulation results more "
             "reproducible, Pogona by default uses"
             "`git describe --all --always` "
             "or, alternatively, the current simulator version "
             "to note the state of the codebase with which the simulation "
             "results were produced."
    )
    group.add_argument(
        '--log-file-verbosity',
        help="Verbosity for the log file",
        default='DEBUG',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    )
    group.add_argument(
        '--profile-file',
        help="Name of the profile file, relative to --results-dir. "
             "You can use the following command to generate a graph: "
             "`gprof2dot -f pstats profile.prof -o callingGraph.dot && "
             "dot -Tps callingGraph.dot -o graph.pdf`. "
             "(gprof2dot can be installed via pip, if it isn't already.)",
        default='profile.prof',
    )
    group.add_argument(
        '--profile-tool',
        help="Which profiling tool to use",
        default='NONE',
        choices=['NONE', 'CPROFILE', 'PROFILE'],
    )
    group.add_argument(
        '--log-config',
        help="Write the final assembled configuration to --results-dir.",
        action='store_true',
    )

    args = main_parser.parse_args()
    return args


def setup_logging(
        verbosity='INFO',
        log_file='simulation.log',
        log_file_verbosity='DEBUG',
        results_dir='',
):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # possibly overridden from args later
    # ^ TODO: how does this impact performance?
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(coloredlogs.ColoredFormatter(
        style='{',
        fmt='{asctime} {levelname} {name}:\n\t{message}',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    stream_handler.setLevel(verbosity)
    root_logger.addHandler(stream_handler)

    if results_dir != '':
        os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, log_file)
    file_handler = logging.FileHandler(filename=log_file, mode='w')
    file_handler.setFormatter(logging.Formatter(
        style='{',
        fmt='{asctime} {levelname} {name}: {message}',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.setLevel(log_file_verbosity)
    root_logger.addHandler(file_handler)


def write_versions_file(filename, openfoam_cases_path):
    try:
        pogona_label = subprocess.check_output(
            ["git", "describe", "--always", "--all", "--long"]
        ).strip().decode()
    except subprocess.CalledProcessError as e:  # noqa: F841
        pogona_label = "UNKNOWN VERSION"
        # TODO: see https://www.python.org/dev/peps/pep-0440
        #  for formatting version numbers, and
        #  https://packaging.python.org/guides/single-sourcing-package-version/
        #  on how to keep the version number in one place
    try:
        cases_label = subprocess.check_output(
            ["git", "describe", "--always", "--all", "--long"],
            cwd=openfoam_cases_path,
        ).strip().decode()
    except subprocess.CalledProcessError as e:  # noqa: F841
        cases_label = "UNKNOWN VERSION"
    with open(filename, 'w') as f:
        f.write(f"Pogona: {pogona_label}\n")
        f.write(f"OpenFOAM cases: {cases_label}")


def args_config_params_to_dict(params: typing.List[str]) -> dict:
    """
    Convert params given in the format
    `"a.b.c=value"`
    for overriding the simulation configuration
    to a dictionary.

    `"a.b.c=value"` should lead to `{'a': {'b': {'c': value}}}`,
    where `value` is parsed as YAML.
    """
    result = dict()

    def _insert(_remaining_keys: typing.List[str], _sub_dict: dict, _value):
        if len(_remaining_keys) == 1:
            _sub_dict[_remaining_keys[0]] = _value
            return
        _top_key = _remaining_keys.pop(0)
        if _top_key not in _sub_dict:
            _sub_dict[_top_key] = dict()
        _insert(_remaining_keys, _sub_dict[_top_key], _value)

    for param in params:
        split = param.split(sep='=', maxsplit=1)
        if len(split) != 2:
            raise ValueError(f"\"{param}\" is not a valid parameter "
                             f"definition: Missing '='.")
        key_path = split[0]
        keys = [k.strip() for k in key_path.split(sep='.')]

        # Parse the value as YAML to automatically convert non-strings to
        # the expected type:
        yaml = ruamel.yaml.YAML(typ='safe')
        value = yaml.load(split[1])

        _insert(keys, result, value)
    return result


if __name__ == '__main__':
    start_cli()
