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

import copy
import numpy as np

import pogona as pg


class Molecule:
    def __init__(
            self,
            position: np.ndarray,
            velocity: np.ndarray,
            object_id: int
    ):
        self.position = position
        self.velocity = velocity
        self.id = -1  # proper ID is set by manager
        self.cell_id = -1  # proper ID is set by predictor
        self.object_id = object_id
        self.delta_time_opt = np.inf
        """
        Current estimate of an optimal step size.
        Will only be set if adaptive time stepping is enabled.
        """

    def update(
        self,
        scene_manager: 'pg.SceneManager',
        new_pos_global: np.ndarray,
    ):
        self.position = new_pos_global
        if self.object_id is not None:
            new_cell_id = scene_manager.get_closest_cell_centre_id(
                self.object_id,
                new_pos_global
            )
            if new_cell_id is not None:
                self.cell_id = new_cell_id
        # self.at_boundary = scene_manager.is_at_boundary(molecule.cell_id)

    def __str__(self):
        return (
            f"Molecule {self.id} at {self.position} "
            f"in Object {self.object_id}"
        )

    def copy(self) -> 'Molecule':
        return copy.deepcopy(self)
