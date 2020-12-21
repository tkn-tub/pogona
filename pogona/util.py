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

"""
Miscellaneous utility functions for the Pogona simulator.
"""

from typing import Type, List, Iterable

import itertools
import enum
import numpy as np

import pogona as pg


def check_enum_key(enum_class: Type[enum.Enum], key: str, param_name: str):
    """
    Raise a ValueError if `key` is not a valid key for `enum_class`.
    """
    valid_keys = [m.name for m in enum_class]
    if key not in valid_keys:
        raise ValueError(
            f"`{param_name}` must be one of {valid_keys}. "
            f"\"{key}\" is invalid."
        )


def check_vector(value: list, component_name: str, key: str):
    if not isinstance(value, list):
        raise ValueError(
            f"\"{component_name}\".{key} is a "
            f"{type(value)}, "
            "but should be a list of length 3."
        )
    if len(value) != 3:
        raise ValueError(
            f"\"{component_name}\".{key} is a "
            f"list but is not of length 3. "
            f"Its current value is {value}."
        )
    for v in value:
        if not isinstance(v, float) and not isinstance(v, int):
            raise ValueError(
                f"\"{component_name}\".{key}={value} is not a float vector."
            )
    return True


def mlpmin_to_lps(mlpmin: float) -> float:
    """Convert millilitres per minute to litres per second."""
    return mlpmin * 1e-3 / 60


def mlpmin_to_m3ps(mlpmin: float) -> float:
    """Convert millilitres per minute to cubic metres per second."""
    return mlpmin * 1e-6 / 60


def grouper(iterable: Iterable, n: int, fillvalue=None):
    """
    Iterate over an iterable in n-sized chunks.
    Based on https://stackoverflow.com/a/434411/1018176

    :param iterable:
    :param n:
    :param fillvalue:
    :return:
    """
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def is_power_of_two(n):
    """
    Check if a number is a power of 2.
    Based on https://stackoverflow.com/a/57025941/1018176

    :param n:
    :return: True iff n is a power of 2.
    """
    return (n != 0) and (n & (n-1) == 0)


def get_random_points_in_cube_local(
    n: int,
    rng: np.random.RandomState,
) -> List[np.ndarray]:
    x_positions = rng.rand(n) - 0.5
    y_positions = rng.rand(n) - 0.5
    z_positions = rng.rand(n) - 0.5
    points = np.array([x_positions, y_positions, z_positions])
    vectors = points.T
    return vectors


def get_random_points_in_geometry_local(
    n: int,
    geometry: 'pg.Geometry',
    rng: np.random.RandomState,
) -> List[np.ndarray]:
    points = []
    for _ in range(n):
        is_inside = False
        while not is_inside:
            # All Geometry instances are centered around (0, 0, 0)
            # with maximum width, height, depth of 1, hence offset -0.5:
            x = rng.rand() - 0.5
            y = rng.rand() - 0.5
            z = rng.rand() - 0.5
            is_inside = geometry.is_inside_geometry(
                np.array((x, y, z)))
            if is_inside:
                points.append(np.array((x, y, z)))
    return points
