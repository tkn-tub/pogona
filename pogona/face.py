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

import numpy as np


class Face:
    def __init__(
            self,
            face_id: int,
            position: np.ndarray,
            normalized_normal: np.ndarray,
            distance_to_centre: float
    ):
        self.id = face_id
        self.position = position
        self.normalized_normal = normalized_normal
        self.distance_to_centre = distance_to_centre

    def point_distance_to_face(self, position: np.ndarray):
        # https://stackoverflow.com/questions/3860206/signed-distance-between-plane-and-point
        return np.dot(self.normalized_normal, position - self.position)
