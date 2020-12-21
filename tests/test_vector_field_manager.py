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
import os
import numpy as np
import pytest


TOLERANCE = dict(rtol=1e-5, atol=1e-12)


class VectorFieldMgrSingleton:
    _vfm = None

    @staticmethod
    def get_vector_field_manager():
        if VectorFieldMgrSingleton._vfm is None:
            VectorFieldMgrSingleton._vfm = pg.VectorFieldManager(
                vector_field=pg.VectorFieldParser.parse_folder(
                    folder=os.path.join(
                        os.path.dirname(__file__),
                        '..', 'pogona', 'objects', 'cavity', '0.5'
                    ),
                    walls_patch_names={'fixedWalls'}
                    # 'movingWall', 'frontAndBack'},
                    # ^ Since the cavity mesh is only one cell thick,
                    # it's important not to specify the frontAndBack walls
                    # as walls here.
                    # Otherwise, the Shepard interpolation implementations
                    # will try to make the flow 0 close to these walls.
                ),
                transformation=pg.Transformation()
            )
        return VectorFieldMgrSingleton._vfm


# Sample points obtained in the cavity mesh by manually picking
# some center points from 0.5/C and checking the corresponding flow
# in the file 0.5/U (note that both lists start on the same line).
# You can use paraFoam to check the values, e.g., using
# a ProbeLocation filter.
CELL_CENTER_SAMPLES = np.array([  # point, known flow
    [(0.02125, 0.00125, 0.0025), (-0.00272097, 0.000232748, 0.000511511)],
    [(0.06125, 0.00625, 0.0025), (-0.0340639, -0.00268938, -0.00177142)],
    [(0.01625, 0.06125, 0.0075), (-0.0851024, 0.246834, -0.00633745)],
    [(0.09875, 0.09875, 0.0075), (0.305291, -0.149422, 0.194356)],  # top right
    [(0.09625, 0.09875, 0.0075), (0.409889, -0.128071, 0.117414)]  # ^ neighbor
])


def test_interpolation_nearest_neighbor():
    vfm = VectorFieldMgrSingleton.get_vector_field_manager()
    for sample_point, known_flow in CELL_CENTER_SAMPLES:
        u = vfm.get_flow_by_position(
            simulation_kernel=None,
            position_global=sample_point,
            interpolation_type=pg.Interpolation.NEAREST_NEIGHBOR
        )
        np.testing.assert_allclose(u, known_flow, **TOLERANCE)


def test_interpolation_modified_shepard():
    vfm = VectorFieldMgrSingleton.get_vector_field_manager()

    # Flow should be unchanged at cell centers:
    for sample_point, known_flow in CELL_CENTER_SAMPLES:
        u = vfm.get_flow_by_position(
            simulation_kernel=None,
            position_global=sample_point,
            interpolation_type=pg.Interpolation.MODIFIED_SHEPARD
        )
        np.testing.assert_allclose(u, known_flow, **TOLERANCE)

    # Flow should be decreasing close to the walls:
    p_end = np.array([0.1, 0.0785, 0.0025])  # on right wall
    flows = []
    for dx in np.linspace(start=0, stop=0.005, num=10):
        u = vfm.get_flow_by_position(
            simulation_kernel=None,
            position_global=np.array([p_end[0] - dx, p_end[1], p_end[2]]),
            interpolation_type=pg.Interpolation.MODIFIED_SHEPARD
        )
        flows.append(np.linalg.norm(u))
    # Separate loop so we can inspect `flows` using PDB:
    for prev, flow in zip(flows, flows[1:]):
        assert prev < flow

    # Flow should be 0 at (and beyond?) walls:
    assert flows[0] == pytest.approx(0)

    # TODO: more tests?
