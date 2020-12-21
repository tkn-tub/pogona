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
import scipy.spatial
import logging
from typing import Optional

import pogona as pg

LOG = logging.getLogger(__name__)


class VectorFieldManager:
    def __init__(
            self,
            vector_field: 'pg.VectorField',
            transformation: 'pg.Transformation'
    ):
        self.vector_field_local: 'pg.VectorField' = vector_field
        """
        Vector field in local coordinates relative to the origin of the mesh.
        """
        self.kd_tree_global = scipy.spatial.cKDTree(
            transformation.apply_to_points(vector_field.cell_centres)
        )
        """
        Spatial data structure in the form of a kd-tree with
        cell centre positions in scene-global coordinates.
        """
        self.transformation = transformation

    def get_flow_by_position(
            self,
            simulation_kernel: Optional['pg.SimulationKernel'],
            position_global: np.ndarray,
            interpolation_type: 'pg.Interpolation' = None
    ):
        """
        :param simulation_kernel: If None, interpolation_type *must* be given!
        :param position_global: A position in global coordinates.
        :param interpolation_type: If None, use the interpolation method
            specified in the SimulationKernel.
        :return: The flow vector in the local coordinate system (i.e.,
            you might want to apply some rotation).
        """
        position_local = self.transformation.apply_inverse_to_point(
            position_global
        )
        if interpolation_type is None:
            interpolation_type = simulation_kernel.get_interpolation_method()
        if interpolation_type == pg.Interpolation.NEAREST_NEIGHBOR:
            (
                nearest_cell_centre_distance,
                nearest_cell_centre_id
            ) = self.kd_tree_global.query(position_global)
            return self._make_flow_global(
                flow_local=self.vector_field_local.flow[nearest_cell_centre_id]
            )
        elif interpolation_type == pg.Interpolation.SHEPARD:
            closest_distance, closest_id = self.kd_tree_global.query(
                position_global,
                k=1
            )
            if np.isclose(closest_distance, 0, atol=1e-10):
                # We are at a point where we already know the exact flow
                return self.vector_field_local.flow[closest_id]

            cell_centres_positions_global = (
                self.transformation.apply_to_points(
                    self.vector_field_local.cell_centres
                )
            )
            cell_centres_ids = range(0, len(cell_centres_positions_global))
            cell_centres_distances = scipy.spatial.distance.cdist(
                position_global.reshape((1, 3)),
                cell_centres_positions_global,
                'euclidean'
            )

            weights = np.true_divide(
                1, np.power(cell_centres_distances, 4)
            )
            values_local = np.array([
                self.vector_field_local.flow[index]
                for index in cell_centres_ids
            ])
            interpolation_local = (
                np.sum(np.multiply(values_local.T, weights), axis=1)
                / np.sum(weights)
            )
            return self._make_flow_global(flow_local=interpolation_local)
        elif interpolation_type in {
            pg.Interpolation.MODIFIED_SHEPARD,
            pg.Interpolation.MODIFIED_SHEPARD_LINEAR,
            pg.Interpolation.MODIFIED_SHEPARD_SQUARED,
            pg.Interpolation.MODIFIED_SHEPARD_CUBED,
            pg.Interpolation.MODIFIED_SHEPARD_FOURTH
        }:
            (
                nearest_cell_centres_distances,
                nearest_cell_centres_ids
            ) = self.kd_tree_global.query(position_global, k=9)
            closest_centre = nearest_cell_centres_ids[0]
            if np.isclose(nearest_cell_centres_distances[0], 0, atol=1e-10):
                # We are at a point where we already know the exact flow
                return self._make_flow_global(
                    self.vector_field_local.flow[closest_centre]
                )
            if self.is_at_boundary(closest_centre):
                # We are in a boundary cell, switch interpolation method
                faces_local = self.vector_field_local.boundary_faces[
                    closest_centre
                ]
                minimum_ratio = np.inf
                for face_local in faces_local:
                    distance_to_boundary_face = (
                        pg.VectorFieldParser.point_distance_to_plane(
                            position_local, face_local)
                    )
                    ratio = (
                        distance_to_boundary_face
                        / face_local.distance_to_centre
                    )
                    if ratio < minimum_ratio:
                        minimum_ratio = ratio
                if minimum_ratio < 0:
                    # We are outside of the mesh, no flow here
                    return self._make_flow_global(np.array((0, 0, 0)))
                else:
                    # TODO: remove this debugging check:
                    _flow_local = self.vector_field_local.flow[closest_centre]
                    if np.linalg.norm(_flow_local * minimum_ratio) > 2:  # m/s
                        LOG.warning(
                            f"Flow in cell {closest_centre} for molecule "
                            f"at position {position_global} "
                            f"(local={position_local}) "
                            f"is |{_flow_local} m/s * {minimum_ratio}| = "
                            f"|{_flow_local * minimum_ratio}| m/s = "
                            f"{np.linalg.norm(_flow_local * minimum_ratio)} "
                            "m/s. "
                            f"The boundary faces are {faces_local} and their "
                            "distances to centre are "
                            + str([
                                face.distance_to_centre
                                for face in faces_local
                            ])
                            + " while the molecule's distance "
                              "to each face are "
                            + str([
                                pg.VectorFieldParser.point_distance_to_plane(
                                    position_local,
                                    face_local
                                )
                                for face_local in faces_local
                            ])
                        )
                    return self._make_flow_global(
                        self.vector_field_local.flow[closest_centre]
                        * minimum_ratio
                    )
            else:
                if (interpolation_type ==
                        pg.Interpolation.MODIFIED_SHEPARD_LINEAR):
                    power = 1
                elif (interpolation_type ==
                        pg.Interpolation.MODIFIED_SHEPARD_SQUARED):
                    power = 2
                elif (interpolation_type ==
                        pg.Interpolation.MODIFIED_SHEPARD_CUBED):
                    power = 3
                elif (interpolation_type ==
                        pg.Interpolation.MODIFIED_SHEPARD_FOURTH):
                    power = 4
                else:
                    power = 1

                # Do actual Inverse Distance Weighting
                values_local = np.array([
                    self.vector_field_local.flow[index]
                    for index in nearest_cell_centres_ids
                ])
                radius = np.amax(nearest_cell_centres_distances)
                weights = np.power(
                    np.true_divide(1, nearest_cell_centres_distances) -
                    np.true_divide(1, radius),
                    power)
                # Normalize the weights such that they sum up to 1
                normalized_weights = np.true_divide(weights, np.sum(weights))

                interpolation_local = (
                    np.sum(
                        np.multiply(values_local.T, normalized_weights),
                        axis=1
                    )
                )
                return self._make_flow_global(interpolation_local)
        else:
            raise NotImplementedError(
                f"Interpolation type {interpolation_type.name} "
                f"is not implemented yet"
            )

    def _make_flow_global(self, flow_local: np.ndarray):
        """Ensure that flow points in the correct direction."""
        return self.transformation.apply_to_direction(flow_local)

    def get_closest_cell_centre_id(
            self,
            position_global: np.ndarray
    ) -> np.ndarray:
        (
            nearest_cell_centre_distance, nearest_cell_centre_id
        ) = self.kd_tree_global.query(position_global)
        return nearest_cell_centre_id

    def get_mesh(self):
        return self.vector_field_local.cell_centres

    def get_cell_centres_local(self):
        """
        Get cell center points of this vector field in local coordinates.
        """
        return self.vector_field_local.cell_centres

    def get_cell_centres_global(self):
        """
        Get cell center points of this vector field in global coordinates.
        WARNING: Expensive operation; generates new array with transformed
        positions!
        """
        return self.transformation.apply_to_points(
            self.vector_field_local.cell_centres
        )

    def get_cell_ids(self):
        return range(len(self.vector_field_local.cell_centres))

    def is_at_boundary(self, cell_id):
        return self.vector_field_local.at_boundary[cell_id]
