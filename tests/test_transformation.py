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
import numpy as np


TOLERANCE = dict(rtol=1e-5, atol=1e-12)
"""
Tolerances for `np.testing.assert_allclose`.
For the meaning of rtol and atol, also check the documentation of
`pytest.approx`.
"""


def test_translation():
    t = pg.Transformation(translation=np.array([1, 2, 3]))
    p = np.array([5, 1, 2.5])
    pp = t.apply_to_point(p)
    np.testing.assert_allclose(pp, [6, 3, 5.5], **TOLERANCE)


def test_rotation():
    t = pg.Transformation(
        rotation=np.array([0, 0, np.pi / 2])
    )
    p = np.array([1, 0, 0])
    pp = t.apply_to_point(p)
    np.testing.assert_allclose(pp, [0, 1, 0], **TOLERANCE)

    t = pg.Transformation(rotation=np.array([np.pi, 0, np.pi / 2]))
    p = np.array([1, 0, 0])
    pp = t.apply_to_point(p)
    np.testing.assert_allclose(pp, [0, 1, 0], **TOLERANCE)


def test_translation_rotation_scale():
    t = pg.Transformation(
        translation=np.array([1, 2, 3]),
        rotation=np.deg2rad([45, 135, 90]),
        scaling=np.array([1.5, 2, 2.5])
    )
    p = np.array([1, 0, 0])
    pp = t.apply_to_point(p)
    # Reference from Blender:
    np.testing.assert_allclose(pp, [1, 0.93934, 1.93934], **TOLERANCE)


def test_inverse():
    t = pg.Transformation(
        translation=np.array([1, 2, 3]),
        rotation=np.deg2rad([45, 135, 90]),
        scaling=np.array([1.5, 2, 2.5])
    )
    p = np.array([42, 1337, 2])
    np.testing.assert_allclose(
        p,
        t.apply_inverse_to_point(t.apply_to_point(p)),
        **TOLERANCE
    )


def test_chaining():
    """
    Concatenation of transformations.
    Test values verified/obtained with Blender.
    """
    p = np.array([1, 2, 3])
    t1 = pg.Transformation(
        translation=np.array([-.02, .35, 1]),
        rotation=np.deg2rad([30, 22, 278]),
        scaling=np.array([.1, 1.1, .56])
    )
    np.testing.assert_allclose(
        t1.apply_to_point(p),
        [1.18099, -0.541337, 3.33142],
        **TOLERANCE
    )
    t2 = pg.Transformation(
        translation=np.array([-.2, -.3, -.4]),
        rotation=np.deg2rad([1, 2, 3]),
        scaling=np.array([2, .3, .4])
    )
    # First execute t1, then t2:
    t3 = t2.apply_to_transformation(t1)
    np.testing.assert_allclose(
        t3.apply_to_point(p),
        [2.21336, -0.359409, 0.846289],
        **TOLERANCE
    )
