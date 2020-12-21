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

from typing import Optional

import pogona as pg
import numpy as np
import os
import shutil
import pandas as pd


class CavityObject(pg.Object):
    def __init__(self):
        super().__init__()

    def get_path(self, use_latest_time_step=True, fallback=False) -> str:
        path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', 'pogona', 'objects', 'cavity'
        )
        return os.path.join(path, self.find_latest_time_step(path))

    def process_changed_inlet_flow_rate(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            inlet_name: str, flow_rate: float
    ):
        pass

    def get_outlet_area(
            self,
            outlet_name: str
    ) -> ('pg.Geometry', 'pg.Transformation'):
        pass

    def get_mesh_index(self) -> str:
        return 'cavity_test'

    @property
    def _openfoam_cases_subpath(self):
        return None

    def get_fallback_mesh_index(self) -> Optional[str]:
        return None


def run_test(
        integration_method: 'pg.Integration',
        results_dir: str,
        remove_sim_results: bool = True,
):
    """
    Set up a very simple simulation with just the cavity mesh.
    No injectors, no sensors.

    :param integration_method:
    :return:
    """
    # Reference data obtained from ParaView:
    # Add a StreamTracer, set integration direction to FORWARD,
    # integrator type to Runge-Kutta 4-5, maximum streamline length 0.8,
    # seed type to Point Source, sphere parameters to center
    # (0.05, 0.05, 0.0075), radius 0, number of points to 1.
    # Then File > Save data…, precision 8, field association: Points
    reference_data = pd.read_csv(os.path.join(
        os.path.dirname(__file__),
        'test_movement_predictor_stream-tracer-0.05-0.05-0.0075.csv'
    ))
    reference_data = reference_data.rename(columns={
        'IntegrationTime': 'integration_time',
        'Points:0': 'x',
        'Points:1': 'y',
        'Points:2': 'z',
    })
    start_positions = np.array([[0.05, 0.05, 0.0075]])

    pg.setup_logging(results_dir=results_dir)
    simulation_kernel, components = pg.SceneManager.construct_from_config(
        filename=os.path.join(
            os.path.dirname(__file__),
            'test_movement_predictor.config.yaml'  # TODO: create config
        ),
        openfoam_cases_path='',
        additional_component_classes={'CavityObject': CavityObject},
        results_dir=results_dir,
        override_config=dict(
            movement_predictor=dict(integration_method=integration_method.name)
        )
    )
    simulation_kernel.initialize_components()
    for start_position in start_positions:
        simulation_kernel.get_molecule_manager().add_molecule(
            molecule=pg.Molecule(
                position=start_position,
                object_id=0,
                velocity=np.zeros(shape=3),  # initial value
            )
        )
    assert (
        simulation_kernel.get_movement_predictor().get_integration_method()
        == integration_method
    )
    simulation_kernel.start(skip_initialization=True)

    sim_data = pd.read_csv(os.path.join(
        results_dir,
        'molecule_positions',
        'positions.csv.319'
        # ^ corresponds approx. to last time step in reference data
    ))
    sim_row = sim_data.iloc[0]
    sim_point = np.array((sim_row.x, sim_row.y, sim_row.z))
    ref_row = reference_data.iloc[-1]
    ref_point = np.array((ref_row.x, ref_row.y, ref_row.z))
    np.testing.assert_allclose(sim_point, ref_point, rtol=0.2, atol=1e-20)
    # TODO: too tolerant?

    if remove_sim_results:
        shutil.rmtree(results_dir)


def test_runge_kutta():
    results_dir = os.path.join(
        os.path.dirname(__file__),
        'test_movement_predictor_results_rk4'
    )
    run_test(
        integration_method=pg.Integration.RUNGE_KUTTA_4,
        results_dir=results_dir,
        remove_sim_results=False
    )


def test_runge_kutta_fehlberg():
    results_dir = os.path.join(
        os.path.dirname(__file__),
        'test_movement_predictor_results_rkf'
    )
    run_test(
        integration_method=pg.Integration.RUNGE_KUTTA_FEHLBERG,
        results_dir=results_dir,
        remove_sim_results=False
    )
