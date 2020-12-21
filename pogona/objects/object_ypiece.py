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
import logging
import numpy as np


LOG = logging.getLogger(__name__)


class ObjectYPiece(pg.Object):
    name = prop.StrProperty("Y-Piece", required=False)
    """The name of this object."""
    radius = prop.FloatProperty(0.00075, required=True)
    """Radius of the outlet tube in meters."""
    angle = prop.FloatProperty(30.0, required=True)
    """Angle between outlet and particle inlet in degrees."""
    outlet_length = prop.FloatProperty(0.04, required=True)
    """Length of the outlet tube in meters."""
    outlet_zone = prop.FloatProperty(0.005, required=False)
    """
    For teleporting: If a molecule enters this zone at the end of the
    outlet tube, it will be teleported to a connected object.
    """
    background_inlet_length = prop.FloatProperty(0.01, required=False)
    """Length of the background flow inlet in meters."""
    injection_inlet_length = prop.FloatProperty(0.04, required=False)
    """Length of the particle injection inlet tube in meters."""
    flow_rate_injection = prop.FloatProperty(0.0, required=True)
    """Flow rate in the injection tube in ml/min."""
    flow_rate_background = prop.FloatProperty(5.0, required=True)
    """Background flow rate in ml/min."""
    variant = prop.StrProperty('', required=False)
    """
    Additional variant information.

    If given, look for an OpenFOAM case with '_<variant>' appended
    to its path name.
    """
    fallback_background_rate_mlpmin = prop.FloatProperty(5.0, required=False)
    """
    Fallback background flow rate for making sensor subscriptions possible
    in the case that this Object starts with an overall flow rate of 0
    (i.e., `is_active == False`).
    """
    fallback_injection_rate_mlpmin = prop.FloatProperty(0.0, required=False)
    """
    Fallback injection flow rate for making sensor subscriptions possible
    in the case that this Object starts with an overall flow rate of 0
    (i.e., `is_active == False`).
    """

    def __init__(self):
        super().__init__()

        # Do this for documentation purposes, it's not code relevant
        self.inlets.append("background")
        self.inlets.append("injection")
        self.outlets.append("outlet")

        self._walls_patch_names.update({'yConnectorPatch'})

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if (max(self._transformation.scaling) > 1.001
                    or min(self._transformation.scaling) < 0.999):
                LOG.warning(
                    "You are trying to scale a y-piece mesh by a factor of "
                    f"{self._transformation.scaling}. Keep in mind that "
                    "this mesh already has an inherent scale from the "
                    "OpenFOAM simulation."
                )
            self._is_active = not np.isclose(
                self.flow_rate_injection + self.flow_rate_background,
                0,
                atol=1e-20
            )
        elif init_stage == pg.InitStages.SET_UP_FLOW_SYSTEM:
            # self.process_changed_inlet_flow_rate(
            #     simulation_kernel=simulation_kernel,
            #     inlet_name="background",
            #     flow_rate=self.flow_rate_background,
            # )

            # Calling this once for just one of the inlets should suffice,
            # since we only want to load the appropriate mesh, and
            # the variables for all flow rates should already be set:
            self.process_changed_inlet_flow_rate(
                simulation_kernel=simulation_kernel,
                inlet_name="injection",
                flow_rate=self.flow_rate_injection,
            )

    @property
    def _openfoam_cases_subpath(self):
        return "y_connector"

    def process_changed_inlet_flow_rate(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            inlet_name: str,
            flow_rate: float
    ):
        if inlet_name == "background":
            self.flow_rate_background = flow_rate
        elif inlet_name == "injection":
            self.flow_rate_injection = flow_rate
        self._is_active = not np.isclose(
            self.flow_rate_injection + self.flow_rate_background,
            0,
            atol=1e-20
        )
        if self._is_active:
            self.load_current_vector_field(simulation_kernel)
        # TODO: never tested an inactive ObjectYPiece,
        #  *should* work as in ObjectTube, though
        simulation_kernel.get_scene_manager().process_changed_outlet_flow_rate(
            simulation_kernel,
            self,
            "outlet",
            self.flow_rate_injection + self.flow_rate_background
        )

    def get_outlet_area(self, outlet_name: str) -> (
            'pg.Geometry',
            'pg.Transformation'
    ):
        if outlet_name != "outlet":
            raise ValueError(
                f"Outlet \"{outlet_name}\" not found! "
                "This y-piece only has one outlet named 'outlet'."
            )
        geometry = pg.Geometry(pg.Shapes.CYLINDER)
        local_transformation = pg.Transformation(
            translation=np.array([
                0,
                0,
                self.outlet_length - self.outlet_zone / 2
            ]),
            scaling=np.array([
                self.radius * 2, self.radius * 2, self.outlet_zone
            ])
        )
        return (
            geometry,
            self._transformation.apply_to_transformation(local_transformation)
        )

    def get_ypiece_mesh_index(
            self,
            injection_rate_mlpmin: float,
            background_rate_mlpmin: float,
    ) -> str:
        return (
            f'y-piece_r{self.radius * 1e3:.2f}mm_'
            f'bg{round(background_rate_mlpmin, 1):g}mlpmin_'
            f'in{round(injection_rate_mlpmin, 1):g}mlpmin_'
            f'o{self.outlet_length * 100:.0f}cm_'
            f'bg{self.background_inlet_length * 100:.0f}cm_'
            f'p{self.injection_inlet_length * 100:.0f}cm'
            + (f'_{self.variant}' if self.variant != '' else '')
        )

    def get_mesh_index(self):
        return self.get_ypiece_mesh_index(
            injection_rate_mlpmin=self.flow_rate_injection,
            background_rate_mlpmin=self.flow_rate_background,
        )

    def get_fallback_mesh_index(self) -> Optional[str]:
        return self.get_ypiece_mesh_index(
            injection_rate_mlpmin=self.fallback_injection_rate_mlpmin,
            background_rate_mlpmin=self.fallback_background_rate_mlpmin,
        )
