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
import logging

LOG = logging.getLogger(__name__)


class ObjectTube(pg.Object):
    name = prop.StrProperty("Tube", required=False)

    radius = prop.FloatProperty(0.00075, required=True)
    """Radius of the tube in m."""
    length = prop.FloatProperty(0.05, required=True)
    """Length of the tube in m."""
    inlet_zone = prop.FloatProperty(0.05, required=False)
    """
    Length of the inlet zone in m.

    This segment at the start of the tube mesh will be cut off,
    since the OpenFOAM simulation showed that the flow profile
    before this threshold does not yet match the analytically
    determined profile of a tube to a sufficient degree.

    'Cut off' here means that this ObjectTube will be shifted
    along its axis such that it will appear as though you are
    dealing with a tube that is simply `inlet_zone` metres shorter.
    """
    outlet_zone = prop.FloatProperty(0.005, required=False)
    """
    For teleporting: If a molecule enters this zone at the end of the
    tube, it will be teleported to a connected object.
    """
    flow_rate = prop.FloatProperty(5, required=True)
    """Flow rate in ml/min."""
    mesh_resolution = prop.IntProperty(11, required=False)
    """
    Mesh resolution, defined as number of
    'radius cells' in the OpenFOAM blockMeshDict.
    """
    variant = prop.StrProperty('', required=False)
    """
    Additional variant information.

    If given, look for an OpenFOAM case with '_<variant>' appended
    to its path name.
    """
    fallback_flow_rate = prop.FloatProperty(5, required=False)
    """
    Fallback flow rate for making sensor subscriptions possible in the
    case that this Object starts with an overall flow rate of 0
    (i.e., `is_active == False`).
    """

    def __init__(self):
        super().__init__()

        # Do this for documentation purposes, its not code relevant
        self.inlets.append("inlet")
        self.outlets.append("outlet")

        # The 5cm tube is useless because the flow does not fully develop
        # TODO: determine this length dynamically depending on available
        #  OpenFOAM cases:
        self._mesh_length_cm = 15
        """
        The actual length of the underlying mesh.
        Should account for both self.length and self.inlet_zone.
        """

        self._walls_patch_names.update({'tubePatch'})

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            shift = pg.Transformation(
                translation=np.array([0, 0, -self.inlet_zone])
            )
            self._transformation = (
                self._transformation.apply_to_transformation(shift)
            )
            if (max(self._transformation.scaling) > 1.001
                    or min(self._transformation.scaling) < 0.999):
                LOG.warning(
                    "You are trying to scale a tube mesh by a factor of "
                    f"{self._transformation.scaling}. Keep in mind that "
                    "this mesh already has an inherent scale from the "
                    "OpenFOAM simulation."
                )
            if self.length + self.inlet_zone > 0.15:
                # TODO: determine this dynamically based on available cases
                raise ValueError(
                    "No path to OpenFOAM simulation files is known for a tube "
                    "that is longer than 0.15 m. "
                    f"Selected length: {self.length} m. "
                    f"Keep in mind that the inlet zone of {self.inlet_zone} m "
                    "is not usable."
                )
            self._is_active = not np.isclose(self.flow_rate, 0, atol=1e-20)
        elif init_stage == pg.InitStages.SET_UP_FLOW_SYSTEM:
            self.process_changed_inlet_flow_rate(simulation_kernel, "inlet",
                                                 self.flow_rate)

    def get_tube_mesh_index(self, flow_rate_mlpmin: float) -> str:
        return (
            f'tube_r{self.radius * 1e3:.2f}mm_'
            f'l{round(self._mesh_length_cm, 1):g}cm_'
            f'{round(flow_rate_mlpmin, 1):g}mlpmin_'
            f'{self.mesh_resolution}cells'
            + (f'_{self.variant}' if self.variant != '' else '')
        )

    @property
    def _openfoam_cases_subpath(self):
        return "tube"

    def get_mesh_index(self):
        return self.get_tube_mesh_index(flow_rate_mlpmin=self.flow_rate)

    def get_fallback_mesh_index(self) -> Optional[str]:
        return self.get_tube_mesh_index(
            flow_rate_mlpmin=self.fallback_flow_rate
        )

    def process_changed_inlet_flow_rate(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            inlet_name: str,
            flow_rate: float
    ):
        self._is_active = not np.isclose(flow_rate, 0, atol=1e-20)
        self.flow_rate = flow_rate
        if self._is_active:
            self.load_current_vector_field(simulation_kernel=simulation_kernel)
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
            translation=np.array((
                0,
                0,
                self.inlet_zone + self.length - self.outlet_zone / 2
            )),
            scaling=np.array((
                self.radius * 2, self.radius * 2, self.outlet_zone
            ))
        )
        return (
            geometry,
            self._transformation.apply_to_transformation(local_transformation)
        )
