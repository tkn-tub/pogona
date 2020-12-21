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

import pogona as pg
import pogona.properties as prop


class SensorDestructing(pg.Sensor):
    turned_on = prop.BoolProperty(True, required=False)

    def __init__(self):
        super().__init__()

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)

    def process_molecule_moving_after(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        if self.turned_on and self.is_inside_sensor_zone(
                position_global=molecule.position):
            simulation_kernel.destroy_molecule(molecule)

    def turn_on(self):
        self.turned_on = True

    def turn_off(self):
        self.turned_on = False
