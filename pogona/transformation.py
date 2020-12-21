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

from typing import Sequence, Optional, Tuple

import numpy as np


class Transformation:

    def __init__(
            self,
            translation: np.ndarray = np.array((0, 0, 0)),
            rotation: np.ndarray = np.array((0, 0, 0)),
            scaling: np.ndarray = np.array((1, 1, 1)),
            matrix: Optional[np.ndarray] = None,
            direction_matrix: Optional[np.ndarray] = None,
            rotation_order: str = 'XYZ'
    ):
        """
        Scaling is applied first, then rotation, then translation!

        :param translation:
        :param rotation: Rotation vector in radians.
        :param scaling:
        :param matrix: Instead of translation, rotation and scaling,
            provide combined matrix instead
        :param direction_matrix: Must be given together with matrix.
        :param rotation_order: Order for computing the rotation matrix.
            Blender's default is also 'XYZ'.
        """
        self._translation = translation
        self._rotation = rotation
        self._scaling = scaling
        self._rotation_order = rotation_order
        self._translation_matrix = generate_translation_matrix(translation)
        self._rotation_matrix = generate_rotation_matrix(
            rotation,
            order=self._rotation_order
        )
        self._scaling_matrix = generate_scaling_matrix(scaling)

        self._matrix: np.ndarray
        self._inverse_matrix: np.ndarray
        self._direction_matrix: np.ndarray
        self._inverse_direction_matrix: np.ndarray
        self._update_matrix()

        if matrix is not None or direction_matrix is not None:
            if matrix is None or direction_matrix is None:
                raise ValueError("If either matrix or direction_matrix is "
                                 "given, the other must be given, too.")
            self._was_set_from_matrix = True
            # Ignore everything we just did and just replace the matrices:
            self._matrix = matrix
            self._inverse_matrix = np.linalg.inv(self._matrix)
            self._direction_matrix = direction_matrix
            self._inverse_direction_matrix = np.linalg.inv(
                self._direction_matrix
            )

            self._translation, _, self._scaling = decompose_matrix(matrix)
        else:
            self._was_set_from_matrix = False

    def apply_to_transformation(self, other: 'Transformation'):
        """
        Works as if you were to first apply `other` to a point,
        then this transformation afterwards.
        """
        translation, rotation_mat, scale = decompose_matrix(
            self._matrix @ other.matrix
        )
        result = Transformation(
            matrix=self._matrix @ other.matrix,
            direction_matrix=self._direction_matrix @ other.direction_matrix
        )
        return result

    def apply_to_point(self, point: np.ndarray):
        transformed_point = self._matrix @ np.append(point, 1.0)
        return transformed_point[:3]

    def apply_to_direction(self, vec: np.ndarray):
        transformed_vec = self._direction_matrix @ np.append(vec, 1.0)
        return transformed_vec[:3]

    def apply_inverse_to_point(self, point: np.ndarray):
        transformed_point = self._inverse_matrix @ np.append(point, 1.0)
        return transformed_point[:3]

    def apply_inverse_to_direction(self, vec: np.ndarray):
        transformed_vec = self._inverse_direction_matrix @ np.append(vec, 1.0)
        return transformed_vec[:3]

    def apply_to_points(
            self,
            points: Sequence[np.ndarray]
    ) -> np.ndarray:
        return apply_transformation_matrix_to_vectors(self._matrix, points)

    def apply_to_directions(
            self,
            vecs: Sequence[np.ndarray]
    ) -> np.ndarray:
        return apply_transformation_matrix_to_vectors(
            self._direction_matrix,
            vecs
        )

    def apply_inverse_to_points(
            self,
            points: Sequence[np.ndarray]
    ) -> np.ndarray:
        return apply_transformation_matrix_to_vectors(
            self._inverse_matrix,
            points
        )

    def apply_inverse_to_directions(
            self,
            vecs: Sequence[np.ndarray]
    ):
        return apply_transformation_matrix_to_vectors(
            self._inverse_direction_matrix,
            vecs
        )

    def _update_matrix(self):
        """Scaling is applied first, then rotation, then translation!"""
        self._matrix = (
            self._translation_matrix
            @ self._rotation_matrix
            @ self._scaling_matrix
        )
        self._inverse_matrix = np.linalg.inv(self._matrix)
        self._direction_matrix = (
            self._rotation_matrix
            @ self._scaling_matrix
        )
        self._inverse_direction_matrix = np.linalg.inv(self._direction_matrix)

    @property
    def was_set_from_matrix(self):
        """
        If true, this transformation was initialized with a given
        matrix, which means we don't know the translation, rotation, or
        scale for sure.
        """
        return self._was_set_from_matrix

    @property
    def matrix(self) -> np.ndarray:
        return self._matrix

    @property
    def direction_matrix(self) -> np.ndarray:
        return self._direction_matrix

    @property
    def inverse_matrix(self) -> np.ndarray:
        return self._inverse_matrix

    @property
    def inverse_direction_matrix(self) -> np.ndarray:
        return self._inverse_direction_matrix

    @property
    def translation(self) -> np.ndarray:
        return self._translation

    @translation.setter
    def translation(self, translation: np.ndarray):
        self._translation = translation
        self._translation_matrix = generate_translation_matrix(translation)
        self._update_matrix()

    @property
    def rotation(self) -> np.ndarray:
        if self.was_set_from_matrix:
            raise Warning("This Transformation instance was initialized with "
                          "a given matrix. The rotation vector returned by "
                          "this method may therefore be inaccurate.")
            # TODO: there are ways to figure out *a* valid rotation vector…
        return self._rotation

    @rotation.setter
    def rotation(self, rotation: np.ndarray):
        self._rotation = rotation
        self._rotation_matrix = generate_rotation_matrix(rotation)
        self._update_matrix()

    @property
    def scaling(self) -> np.ndarray:
        return self._scaling

    @scaling.setter
    def scaling(self, scaling: np.ndarray):
        self._scaling = scaling
        self._scaling_matrix = generate_scaling_matrix(scaling)
        self._update_matrix()

    def __repr__(self):
        return (
            "Transformation("
            f"translation={self.translation}, "
            f"rotation={self.rotation}, "
            f"scaling={self.scaling}"
            ")"
        )


def apply_transformation_matrix_to_vectors(
        matrix: np.ndarray,
        vectors: Sequence[np.ndarray]
) -> np.ndarray:
    # Add a fourth column of ones for homogeneous coordinates:
    point_matrix = np.concatenate(
        [vectors, np.ones((len(vectors), 1))],
        axis=1
    )
    transformed_list = (matrix @ point_matrix.T).T
    return transformed_list[:, :3]


def generate_translation_matrix(translation_vector: np.ndarray) -> np.ndarray:
    return np.array((
        (1, 0, 0, translation_vector[0]),
        (0, 1, 0, translation_vector[1]),
        (0, 0, 1, translation_vector[2]),
        (0, 0, 0, 1)
    ))


def generate_scaling_matrix(scaling_vector: np.ndarray) -> np.ndarray:
    return np.array((
        (scaling_vector[0], 0, 0, 0),
        (0, scaling_vector[1], 0, 0),
        (0, 0, scaling_vector[2], 0),
        (0, 0, 0, 1)
    ))


def generate_rotation_matrix(
        rotation_vector: np.ndarray,
        order: str = 'XYZ'
) -> np.ndarray:
    """
    :param rotation_vector:
    :param order:
    :return:
    """
    rx = np.array((
        (1, 0, 0, 0),
        (0, np.cos(rotation_vector[0]), -np.sin(rotation_vector[0]), 0),
        (0, np.sin(rotation_vector[0]), np.cos(rotation_vector[0]), 0),
        (0, 0, 0, 1)
    ))
    ry = np.array((
        (np.cos(rotation_vector[1]), 0, np.sin(rotation_vector[1]), 0),
        (0, 1, 0, 0),
        (-np.sin(rotation_vector[1]), 0, np.cos(rotation_vector[1]), 0),
        (0, 0, 0, 1)
    ))
    rz = np.array((
        (np.cos(rotation_vector[2]), -np.sin(rotation_vector[2]), 0, 0),
        (np.sin(rotation_vector[2]), np.cos(rotation_vector[2]), 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1)
    ))
    # Seems like we have to multiply the matrices in reverse order
    # to match Blender's definition:
    if order == 'XYZ':
        return rz @ ry @ rx
    if order == 'YXZ':
        return rz @ rx @ ry
    if order == 'XZY':
        return ry @ rz @ rx
    if order == 'ZXY':
        return ry @ rx @ rz
    if order == 'ZYX':
        return rx @ ry @ rz
    if order == 'YZX':
        return rx @ rz @ ry
    raise ValueError(f"Invalid order \"{order}\"")


def decompose_matrix(
        mat: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Decompose a given transformation matrix into translation vector,
    rotation matrix, and scaling vector.
    This is not guaranteed to work for transformation matrices
    that are not coming from our Transformation class.
    """
    # With help from https://math.stackexchange.com/a/1463487
    # Translation: last column
    translation = mat[:, 3][:3]
    # Scale: length of the first three column vectors
    scale = np.linalg.norm(mat[:3, :3], axis=0)
    # Rotation matrix:
    rotation_mat = np.concatenate(
        (
            [
                np.append(np.true_divide(mat[:3, i], scale[i]), 0)
                for i in range(3)
            ],
            [[0, 0, 0, 1]],
        ),
        axis=0
    ).T  # TODO: to vector
    return translation, rotation_mat, scale


def generate_identity_matrix() -> np.array:
    matrix = np.zeros((4, 4), int)
    np.fill_diagonal(matrix, 1)
    return matrix
