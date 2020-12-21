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

from abc import ABCMeta
import numpy as np

import pogona as pg
import pogona.properties as prop


class Sensor(pg.Component, metaclass=ABCMeta):
    translation = prop.VectorProperty([0, 0, 0], required=True)
    rotation = prop.VectorProperty([0, 0, 0], required=True)
    scale = prop.VectorProperty([1, 1, 1], required=True)
    shape = prop.EnumProperty(
        str(pg.Shapes.NONE.name),
        name='shape',
        required=True,
        enum_class=pg.Shapes,
    )
    """
    Shape of this sensor.
    Valid shapes are defined in the :class:`pogona.Shapes` enum.
    """

    def __init__(self):
        super().__init__()
        self.sensor_id: int = -1
        """Unique integer sensor ID. Set by the sensor manager."""
        self._transformation = pg.Transformation()
        """Transformation of this sensor in the scene."""

        self._geometry = pg.Geometry(pg.Shapes.NONE)
        """Geometry of this sensor, set from shape."""

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._geometry = pg.Geometry(shape=pg.Shapes[self.shape])

            self._transformation = pg.Transformation(
                translation=np.array(self.translation),
                rotation=np.array(self.rotation),
                scaling=np.array(self.scale)
            )
        if init_stage == pg.InitStages.REGISTER_SENSORS:
            simulation_kernel.get_sensor_manager().register_sensor(self)

    def process_molecule_moving_before(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule',
    ):
        """
        Called before updating the position of a particle within a time step.
        Useful for SensorTeleporting, for example, which should consider
        the position of particles right after they have been spawned.

        :param simulation_kernel:
        :param molecule:
        :return:
        """
        pass

    def process_molecule_moving_after(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        """
        Override this method for your sensing algorithm.
        The sensor manager will use this method to notify you of all molecule
        movement inside of the sensor zone.
        However, it may also notify you of molecule movement outside of your
        sensor zone!
        So make sure you additionally check the molecule position yourself.
        See SensorCounting for a simple reference implementation.

        :param simulation_kernel: The single simulation kernel
        :param molecule: Which molecule has moved, with the new position
        """
        pass

    def is_inside_sensor_zone(self, position_global: np.ndarray):
        position_local = self._transformation.apply_inverse_to_point(
            position_global
        )
        return self._geometry.is_inside_geometry(position_local)

    @property
    def transformation(self) -> 'pg.Transformation':
        return self._transformation
