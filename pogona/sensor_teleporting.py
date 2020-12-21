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
from typing import Optional, cast

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SensorTeleporting(pg.Sensor):
    """Teleports molecules from one object to another."""

    source_object = prop.ComponentReferenceProperty(
        '',
        required=True,
        can_be_empty=False,
    )
    """Component name of the source object."""
    source_outlet_name = prop.StrProperty('', required=True)
    """Name of the outlet in the source mesh (check your OpenFOAM mesh)."""
    target_object = prop.ComponentReferenceProperty(
        '',
        required=True,
        can_be_empty=False,
    )
    """Component name of the target object."""
    target_inlet_name = prop.StrProperty('', required=True)
    """Name of the inlet in the target mesh (check your OpenFOAM mesh)."""

    def __init__(self):
        super().__init__()

        self._source_object: Optional['pg.Object'] = None
        self._target_object: Optional['pg.Object'] = None

        # Remove mandatory arguments from the Sensor class that will be
        # set automatically in the BUILD_SCENE initialization stage
        # (or at least their corresponding results will, i.e.,
        # `transformation` and `geometry`):
        self._mandatory_arguments = self._mandatory_arguments - {
            'translation',
            'rotation',
            'scale',
            'shape'
        }

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.BUILD_SCENE:
            self._source_object = cast(
                'pg.Object',
                simulation_kernel.get_components()[self.source_object]
            )
            self._target_object = cast(
                'pg.Object',
                simulation_kernel.get_components()[self.target_object]
            )
            if self.source_outlet_name not in self._source_object.outlets:
                raise ValueError(
                    f"Source Object \"{self.source_object}\" does not have "
                    f"an outlet named \"{self.source_outlet_name}\"."
                )
            if self.target_inlet_name not in self._target_object.inlets:
                raise ValueError(
                    f"Target Object \"{self.target_object}\" does not have "
                    f"an inlet named \"{self.target_inlet_name}\"."
                )
            (
                self._geometry,
                self._transformation
            ) = self._source_object.get_outlet_area(self.source_outlet_name)
        if init_stage == pg.InitStages.CREATE_TELEPORTERS:
            simulation_kernel.get_scene_manager().add_interconnection(
                sensor_teleporting=self
            )

    def get_source_object(self) -> 'pg.Object':
        return self._source_object

    def get_target_object(self) -> 'pg.Object':
        return self._target_object

    def process_molecule_moving_before(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        if (molecule.object_id == self._source_object.object_id
                and self.is_inside_sensor_zone(
                    position_global=molecule.position)):
            molecule.object_id = self._target_object.object_id
            molecule.cell_id = (
                simulation_kernel.get_scene_manager(
                ).get_closest_cell_centre_id(
                    object_id=molecule.object_id,
                    position_global=molecule.position
                )
            )
            LOG.debug(f"SensorTeleporting: Teleporting {molecule}")
