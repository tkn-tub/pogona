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

import math
from typing import Optional

import numpy as np

import pogona as pg
import pogona.properties as prop
import logging

LOG = logging.getLogger(__name__)


class ObjectTubeAnalytical(pg.Object):
    radius = prop.FloatProperty(0.00075, required=True)
    """Radius of the tube in m."""
    length = prop.FloatProperty(0.05, required=False)
    """Length of the tube in m."""
    flow_rate = prop.FloatProperty(5, required=True)
    """Flow rate in ml/min."""
    outlet_zone = prop.FloatProperty(0.5, required=False)
    """Length of the outlet teleporter."""

    def __init__(self):
        super().__init__()
        self.name = "Analytical Tube"

        # Do this for documentation purposes, its not code relevant
        self.inlets.append("inlet")
        self.outlets.append("outlet")

        self._flow_speed: float = self.calculate_average_flow()
        """Average flow speed in m/s"""

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        # Do not try to load the vector field for this object
        if init_stage != pg.InitStages.CREATE_DATA_STRUCTURES:
            super().initialize(simulation_kernel, init_stage)

        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if (max(self._transformation.scaling) > 1.001
                    or min(self._transformation.scaling) < 0.999):
                LOG.warning(
                    "You are trying to scale this tube by a factor of "
                    f"{self._transformation.scaling}. Keep in mind that "
                    "this mesh already has an inherent scale, expressed "
                    "in radius and length."
                )
        elif init_stage == pg.InitStages.SET_UP_FLOW_SYSTEM:
            self.process_changed_inlet_flow_rate(simulation_kernel, "inlet", 5)

    def get_flow(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            position_global: np.ndarray,
            sim_time: float
    ):
        position_local = self._transformation.apply_inverse_to_point(
            position_global
        )
        # apply pythagoras
        radial_distance = math.sqrt(
            position_local[0] ** 2
            + position_local[1] ** 2
        )
        # [bird2002transport 5.1-1]
        z_speed = max(
            self._flow_speed * 2 * (1 - (radial_distance / self.radius) ** 2),
            0
        )
        flow_local = np.array((0, 0, z_speed))
        # Apply only the rotation matrix to the resulting flow,
        # because flow vectors have no position and because
        # we can assume for now that nobody would ever want to scale
        # a vector field:
        return self._transformation.apply_to_direction(flow_local)

    def get_path(self, use_latest_time_step=False, fallback=False) -> str:
        """
        :param use_latest_time_step: Find the latest time step in path
        :return: Path to the OpenFOAM files for this object.
        """
        return ""

    def process_changed_inlet_flow_rate(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            inlet_name: str,
            flow_rate: float
    ):
        self.flow_rate = flow_rate
        self._flow_speed = self.calculate_average_flow()
        simulation_kernel.get_scene_manager().process_changed_outlet_flow_rate(
            simulation_kernel,
            self,
            "outlet",
            flow_rate
        )

    def get_outlet_area(self, outlet_name: str) -> (
            'pg.Geometry',
            'pg.Transformation'
    ):
        if outlet_name != 'outlet':
            raise ValueError(
                "Outlet not found! "
                "This pipe only has one outlet named 'outlet'."
            )
        geometry = pg.Geometry(pg.Shapes.CYLINDER)
        # TODO(jdrees): calculate the proper transformation for the
        #  outlet based on the tube length and radius
        local_transformation = pg.Transformation(
            translation=np.array((0, 0, self.length)),
            scaling=np.array((
                self.radius * 2, self.radius * 2, self.outlet_zone))
        )
        return (
            geometry,
            self._transformation.apply_to_transformation(local_transformation)
        )

    def get_mesh_index(self):
        return "analytical_tube"

    def get_current_mesh_global(self):
        return None

    def get_current_mesh_local(self):
        return None

    def get_vector_field_manager(self):
        return None

    @property
    def _openfoam_cases_subpath(self):
        return None

    def get_fallback_mesh_index(self) -> Optional[str]:
        return None

    def get_closest_cell_centre_id(self, position: np.ndarray):
        return 0

    def calculate_average_flow(self):
        cross_section_area = math.pi * self.radius * self.radius
        LOG.debug(f"Tube cross section area is {cross_section_area} m²")
        # Transform from ml/min to m3/s
        si_flow_rate = pg.util.mlpmin_to_m3ps(self.flow_rate)
        LOG.debug(f"Flow rate is {si_flow_rate} m³/s")
        flow_speed = si_flow_rate / cross_section_area
        LOG.debug(f"Calculated average flow speed is {flow_speed} m/s")
        # maximum flow is 2 times the average [bird2002transport 5.1-2]
        LOG.debug(f"Calculated maximum flow speed is {flow_speed * 2} m/s")
        return flow_speed
