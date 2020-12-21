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
import pogona.properties as prop
import numpy as np


class ObjectPumpVolume(pg.Object):
    name = prop.StrProperty("Static flow pump", required=False)
    flow_rate = prop.IntProperty(0, required=False)

    injection_volume_l = prop.FloatProperty(0.001, required=True)
    injection_flow_mlpmin = prop.FloatProperty(10, required=True)

    def __init__(self):
        super().__init__()
        self.outlets.append("outlet")

        self._t_end_injection: float = 0
        """Simulation time when to end an injection."""

        self._mandatory_arguments -= {
            'scale',
            'rotation',
            'translation',
            'openfoam_cases_path',
        }

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._is_active = False

    def start_injection(
            self,
            simulation_kernel: 'pg.SimulationKernel',
    ):
        """
        Start an injection with the flow speed (`injection_flow`)
        and total volume `injection_volume` configured in this object.
        """

        self._t_end_injection = (
            simulation_kernel.get_simulation_time()
            + self.injection_volume_l / pg.util.mlpmin_to_lps(
                self.injection_flow_mlpmin)
        )
        self._set_current_pump_flow(
            simulation_kernel=simulation_kernel,
            flow_rate=self.injection_flow_mlpmin,
        )
        self._is_active = True

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        """
        Update the pump activity based on the current time (since an
        injection started).
        """

        # Ensure this method is always called after a Modulation instance
        # has made its changes in this time step:
        if notification_stage != pg.NotificationStages.PUMPING:
            return
        if not self._is_active:
            return
        if simulation_kernel.get_simulation_time() < self._t_end_injection:
            return
        self._is_active = False
        self._set_current_pump_flow(
            simulation_kernel=simulation_kernel,
            flow_rate=0,
        )

    def get_mesh_index(self) -> str:
        pass

    def process_changed_inlet_flow_rate(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            inlet_name: str,
            flow_rate: float
    ):
        raise RuntimeError(
            "A pump only has an outlet, "
            "so nothing should be connected to its inlet"
        )

    def get_flow(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            position_global: np.ndarray,
            sim_time: float
    ):
        raise RuntimeError(
            "A pump does not have an actual associated geometry, "
            "molecules should not be inside it."
        )

    def get_outlet_area(self, outlet_name: str) -> (
            'pg.Geometry',
            'pg.Transformation'
    ):
        if outlet_name != "outlet":
            raise ValueError(
                "Outlet not found! "
                "This pump only has one outlet named 'outlet'."
            )
        # The pump doesn't really define any outlet area,
        # so let's use a nonexistent one.
        geometry = pg.Geometry(pg.Shapes.NONE)
        transformation = pg.Transformation()  # identity transformation
        return geometry, transformation

    def set_interpolation_method(
            self,
            interpolation_method: 'pg.Interpolation'
    ):
        pass

    def get_current_mesh_local(self):
        return None

    def get_current_mesh_global(self):
        return None

    @property
    def _openfoam_cases_subpath(self):
        return None

    def get_fallback_mesh_index(self) -> Optional[str]:
        return None

    def get_closest_cell_centre_id(self, position: np.ndarray):
        raise RuntimeError(
            "A pump does not have an actual associated geometry, "
            "molecules should not be inside it."
        )

    def load_current_vector_field(
            self,
            simulation_kernel: 'pg.SimulationKernel'
    ):
        # No need to do anything
        pass

    def _set_current_pump_flow(self, simulation_kernel, flow_rate: float):
        self.flow_rate = flow_rate
        simulation_kernel.get_scene_manager().process_changed_outlet_flow_rate(
            simulation_kernel=simulation_kernel,
            source_object=self,
            outlet_name='outlet',
            flow_rate=flow_rate,
        )

    def get_path(self, use_latest_time_step=False, fallback=False) -> str:
        pass  # Pumps don't need a path
