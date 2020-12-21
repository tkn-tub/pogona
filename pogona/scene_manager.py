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

import csv
from typing import List, Dict, Tuple, Optional, Type, Any

import logging
import os
import inspect
import numpy as np

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SceneManager(pg.Component):
    component_name = prop.StrProperty("scene_manager", required=False)
    """Since this component is not created by the config, choose a name"""

    def __init__(self):
        super().__init__()
        self._objects: List['pg.Object'] = []
        self._teleporters: Dict[
            Tuple[str, str], 'pg.SensorTeleporting'
        ] = dict()
        """
        Instances of teleporting sensors by a tuple of their source object's
        component name and the name of the outlet in the source object.
        """

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)

    def add_object(self, object_to_add: 'pg.Object'):
        LOG.debug(f"Adding {object_to_add.component_name} with mesh index "
                  f"{object_to_add.get_mesh_index()} as "
                  f"ID {len(self._objects)}")
        object_to_add.set_arguments(
            object_id=len(self._objects)
        )
        self._objects.append(object_to_add)

    def add_interconnection(self, sensor_teleporting: 'pg.SensorTeleporting'):
        """Called by SensorTeleporting to register itself."""
        self._teleporters[(
            sensor_teleporting.get_source_object().component_name,
            sensor_teleporting.source_outlet_name
        )] = sensor_teleporting

    def get_flow_by_position(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            position_global: np.ndarray,
            object_id: int,
            sim_time: float
    ):
        flow = self._objects[object_id].get_flow(
            simulation_kernel,
            position_global,
            sim_time
        )
        if True in np.isnan(flow):
            raise AssertionError(
                "Flow is NaN for a molecule at position "
                f"{position_global}."
            )
        return flow

    def process_changed_outlet_flow_rate(
            self,
            simulation_kernel,
            source_object: 'pg.Object',
            outlet_name: str,
            flow_rate: float
    ):
        key = source_object.component_name, outlet_name
        if key not in self._teleporters:
            # No teleporter exists for the outlet of this source object
            # to another object.
            # This is expected behavior when the end of a chain of objects
            # is reached.
            return
        teleporter = self._teleporters[key]
        teleporter.get_target_object().process_changed_inlet_flow_rate(
            simulation_kernel=simulation_kernel,
            inlet_name=teleporter.target_inlet_name,
            flow_rate=flow_rate
        )

    def get_outlets(self, object_id):
        return self._objects[object_id].outlets

    def get_inlets(self, object_id):
        return self._objects[object_id].inlets

    def get_all_objects(self):
        return self._objects

    def plot_to_csv(self, filename):
        with open(filename, mode='w') as csv_file:
            fieldnames = ['name', 'object_id', 'cell_id', 'x', 'y', 'z']
            writer = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )

            writer.writerow(fieldnames)
            for object_to_write in self._objects:
                transformed_mesh = object_to_write.get_current_mesh_global()
                if transformed_mesh is not None:
                    for cell_id, cell_centre in enumerate(transformed_mesh):
                        writer.writerow((
                            object_to_write.name,
                            object_to_write.object_id,
                            cell_id,
                            cell_centre.x,
                            cell_centre.y,
                            cell_centre.z
                        ))

    def get_closest_cell_centre_id(
            self, object_id: int,
            position_global: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        :returns: Array of closest cell centers to `position`.
            If there's only one position, output is squeezed.
            None if the Object instance is inactive.
            See documentation of cKDTree.query().
        """
        return self._objects[object_id].get_closest_cell_centre_id(
            position_global=position_global
        )

    @staticmethod
    def construct_from_config(
            filename: str,
            openfoam_cases_path: str,
            additional_component_classes: Dict[str, Type[Any]] = None,
            override_config: dict = None,
            results_dir: str = '.',
            log_config: bool = False,
    ) -> (
            'pg.SimulationKernel',
            Dict[str, Tuple[Optional['pg.Component'], dict]]
    ):
        """
        Set up the basic scene from a YAML configuration file
        (possibly created with the MaMoKo Blender Add-on).

        :param filename: YAML configuration file, not to be confused with
            the scene *layout* configuration file.
            Typically `config.yaml`.
            `scene.yaml` and `config.yaml` are assumed to have matching
            names in their `objects` entry.
            Where `scene.yaml` defines the object's shape and transformation,
            `config.yaml` defines additional configuration parameters
            for the simulation.
        :param openfoam_cases_path: Path to OpenFOAM cases (should include a
            `tube/` subdirectory). `cache/` will be created here.
        :param additional_component_classes: Dict of additional classes
            to search in when constructing objects.
        :param override_config: If given, this dict will be used to update
            the configuration loaded from `filename`.
        :param results_dir:
        :param log_config:
            Write the final assembled configuration to results_dir.
        :return: the SimulationKernel, and a dictionary
            mapping object names to tuples of the corresponding component
            and its original definition in the configuration.
        """
        if additional_component_classes is None:
            additional_component_classes = dict()

        conf = pg.assemble_config_recursively(
            filename,
            override_conf=override_config
        )
        # ^ Allows configuration inheritance by specifying
        #  an 'inherit' parameter with one filename or a list of filenames.
        if log_config:
            pg.write_config(conf, os.path.join(results_dir, "config.yaml"))

        simulation_kernel = pg.SimulationKernel()
        # The kernel gets the top-level configuration arguments:
        kernel_args = conf.copy()
        kernel_args.pop('components', None)
        kernel_args.pop('scene_layout_file', None)
        if 'mesh_manager' not in kernel_args:
            kernel_args['mesh_manager'] = dict()
        # Give the mesh manager the openfoam_cases_path to be used as the
        # default prefix for its cache path.
        kernel_args['mesh_manager'][
            'openfoam_cases_path'] = openfoam_cases_path
        simulation_kernel.set_arguments(
            results_dir=results_dir,
            **kernel_args
        )

        components: Dict[str, Tuple[Optional['pg.Component'], dict]] = dict()
        conf_components = conf.get('components', dict())

        # Construct components if possible:
        available_classes = locals().copy()
        available_classes.update(
            dict(inspect.getmembers(pg, inspect.isclass))
        )
        available_classes.update(additional_component_classes)
        for name, component_def in conf_components.items():
            component_type = component_def.get('type', None)
            if (
                    component_type not in available_classes
                    or component_type == 'GENERIC'
            ):
                LOG.warning(
                    f"Not constructing object \"{name}\" "
                    f"of type {component_type}.\n"
                    "\tYou can still access its transformation "
                    "and parameters.\n"
                    "\tPlease construct it yourself."
                )
                components[name] = (None, component_def)
                continue

            component_class = available_classes[component_type]
            LOG.info(
                f"Constructing component \"{name}\" of class "
                f"\"{component_class}\"."
            )
            component_instance = component_class()

            kwargs = component_def.copy()
            # Try to remove all properties that the obj_class constructor is
            # probably not prepared for:
            kwargs.pop('type', None)
            kwargs.pop('visualization_scale', None)
            component_instance.set_arguments(
                **kwargs,
                component_name=name,
            )
            if isinstance(component_instance, pg.Object):
                component_instance.set_arguments(
                    openfoam_cases_path=openfoam_cases_path
                )

            components[name] = (component_instance, component_def)
            simulation_kernel.attach_component(component_instance)

        return (
            simulation_kernel,
            components
        )
