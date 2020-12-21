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

from enum import Enum

import numpy as np


class Shapes(Enum):
    CUBE = 1
    """A cube of side length 1 with (0, 0, 0) as its center point."""
    CYLINDER = 2
    """
    A z-axis-aligned cylinder of radius 0.5 and height 1 with (0, 0, 0) as its
    center point.
    """
    SPHERE = 3
    """A sphere of radius 0.5 with (0, 0, 0) as its center point."""
    POINT = 4
    """A single point at (0, 0, 0). Does not support is_inside_geometry."""
    NONE = 5
    """Representation of non-existent geometries."""


class Geometry:
    """
    Common functions defined for various shapes centered around the origin
    (0, 0, 0) with a maximum width, height, and depth of 1.
    """

    def __init__(self, shape: Shapes):
        self.shape = shape

    def is_inside_geometry(self, position_shifted_unit: np.ndarray):
        """
        :param position_shifted_unit: A position local to this Geometry,
            which is confined by a cube between (-0.5, -0.5, -0.5) and
            (0.5, 0.5, 0.5).
        :return:
        """
        if not self.check_basic_box(position_shifted_unit):
            return False
        if self.shape is Shapes.CUBE:
            return True
        elif self.shape is Shapes.CYLINDER:
            return (
                np.square(position_shifted_unit[0])
                + np.square(position_shifted_unit[1])
                <= 0.25  # = 0.5^2
            )
        elif self.shape is Shapes.SPHERE:
            return (
                np.square(position_shifted_unit[0])
                + np.square(position_shifted_unit[1])
                + np.square(position_shifted_unit[2])
                <= 0.25  # = 0.5^2
            )
        elif self.shape is Shapes.NONE:
            return False
        else:
            raise NotImplementedError("Geometry not implemented yet")

    @staticmethod
    def check_basic_box(position_shifted_unit: np.ndarray):
        """
        :param position_shifted_unit: A position local to this Geometry,
            which is confined by a cube between (-0.5, -0.5, -0.5) and
            (0.5, 0.5, 0.5).
        :return:
        """
        return (
            -0.5 <= position_shifted_unit[0] <= 0.5
            and -0.5 <= position_shifted_unit[1] <= 0.5
            and -0.5 <= position_shifted_unit[2] <= 0.5
        )

    def __repr__(self):
        return f"Geometry({self.shape.name})"
