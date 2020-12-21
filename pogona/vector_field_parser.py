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

from typing import Set, cast
import os
import enum
import openfoamparser
import numpy as np
import logging

import pogona as pg

LOG = logging.getLogger(__name__)


class DummyBoundaryPointsVariant(enum.Enum):
    NONE = 1
    FACE_CENTERS = 2
    FACE_POINTS = 3


class VectorFieldParser:
    def __init__(self):
        pass

    @staticmethod
    def parse_folder(
            folder: str,
            walls_patch_names: Set[str],
            dummy_boundary_points: DummyBoundaryPointsVariant = (
                    DummyBoundaryPointsVariant.NONE),
    ) -> 'pg.VectorField':
        """
        :param folder:
        :param walls_patch_names: Which patches to consider as boundaries
            (typically does not include inlets and outlets).
        :param dummy_boundary_points: 'face-centers', 'face-points', or
            'none'/None (default).
        """
        if walls_patch_names is None:
            LOG.warning("Using default wall patch names.")
            walls_patch_names = ('walls', 'yConnectorPatch', 'tubePatch')
        LOG.info("Starting import of " + os.path.realpath(folder))
        # Check if folder exists
        if not os.path.isdir(folder):
            raise NotADirectoryError(
                "The OpenFOAM simulation result folder "
                f"{os.path.realpath(folder)} does not exist. "
                "Are you sure your path configuration is correct?"
            )
        # Check if cell center file exists
        if not os.path.isfile(os.path.join(folder, 'C')):
            raise FileNotFoundError(
                "The openfoam simulation result folder "
                f"{os.path.realpath(folder)} does not contain cell centres. "
                "Run 'postProcess -func writeCellCentres' to generate them."
            )
        LOG.debug("Importing flow...")
        flow = openfoamparser.parse_internal_field(
            os.path.join(folder, 'U')
        )
        LOG.debug("Imported flow. Size: " + str(len(flow)))
        LOG.debug("Importing mesh...")
        mesh = openfoamparser.FoamMesh(os.path.join(folder, '..'))
        LOG.debug("Imported mesh. Size: " + str(mesh.num_cell + 1))
        LOG.debug("Importing cell centres...")
        mesh.read_cell_centres(os.path.join(folder, 'C'))
        centres = mesh.cell_centres
        LOG.debug("Imported cell centres. Size: " + str(len(centres)))
        LOG.debug("Importing boundaries...")
        is_boundary = np.full((len(centres), 1), False)
        LOG.debug("Available boundaries: " + str(mesh.boundary))
        boundary_cells = np.concatenate([
            np.fromiter(mesh.boundary_cells(patch_name.encode()), int)
            for patch_name in walls_patch_names
        ])
        if len(boundary_cells) > 0:
            for centre_id in np.nditer(boundary_cells):
                is_boundary[centre_id] = True
        else:
            LOG.warning(
                "Are you sure this mesh has no boundary cells? "
                f"(Folder \"{folder}\")"
            )
        # Get all faces for the boundary
        boundary_faces = dict()
        centres_to_add = []  # for dummy boundary points
        boundary_faces_to_add = []  # for dummy boundary points
        for face, face_id in zip(mesh.faces, range(0, len(mesh.faces))):
            if True in (
                    mesh.is_face_on_boundary(face_id, patch_name.encode())
                    for patch_name in walls_patch_names
            ):
                cell_id = mesh.owner[face_id]
                # Retrieve the associated point vectors
                face_points = []
                for point_id in face:
                    face_points.append(mesh.points[point_id])
                # Calculate the normal
                position = face_points[0]
                plane_vector_1 = face_points[1] - position
                plane_vector_2 = face_points[2] - position
                normal = np.cross(plane_vector_2, plane_vector_1, axis=0)
                normal = normal / np.linalg.norm(normal)
                # Write temporary face
                temporary_face = pg.Face(face_id, position, normal, 0.0)
                # Calculate distance from cell centre to face
                distance_to_centre = VectorFieldParser.point_distance_to_plane(
                    centres[cell_id],
                    temporary_face
                )
                face_with_distance = pg.Face(
                    face_id,
                    position,
                    normal,
                    distance_to_centre
                )
                # Save into dictionary
                try:
                    boundary_faces[cell_id].append(face_with_distance)
                except KeyError:
                    # This is the first face in this cell,
                    # create a new array for it
                    boundary_faces[cell_id] = [face_with_distance]

                if (
                        dummy_boundary_points
                        == pg.DummyBoundaryPointsVariant.FACE_POINTS
                ):
                    centres_to_add.extend(face_points)
                    # Adding only one boundary face per dummy cell.
                    # TODO: ok?
                    boundary_faces_to_add.extend(
                        [face_with_distance] * len(face_points))
                elif (
                        dummy_boundary_points
                        == pg.DummyBoundaryPointsVariant.FACE_CENTERS
                ):
                    # Define the face center as the point with mean
                    # x, y, and z coordinate of all face points:
                    centres_to_add.append(np.mean(face_points, axis=0))
                    # TODO: see above
                    boundary_faces_to_add.append(face_with_distance)
        LOG.debug(
            "Imported boundaries. Size: " + str(len(boundary_faces.items()))
        )

        # For dummy boundary points:
        if len(centres_to_add) > 0:
            centres_to_add = np.array(centres_to_add)
            print(
                f"centres_to_add: {centres_to_add.shape}, "
                f"centres: {centres.shape}, "
                f"flow: {flow.shape}, "
                f"is_boundary: {is_boundary.shape}, "
                f"adding {len(boundary_faces_to_add)} boundary faces"
            )
            for i, boundary_faces_for_this in enumerate(boundary_faces_to_add):
                boundary_faces[i + len(centres)] = [boundary_faces_for_this]
            centres = np.concatenate((centres, centres_to_add))
            # Boundary points to add have a flow of 0:
            flow = np.concatenate((flow, np.zeros((len(centres_to_add), 3))))
            is_boundary = np.concatenate((
                is_boundary,
                np.full((len(centres_to_add), 1), True)
            ))

        vector_field = pg.VectorField(
            cell_centres=centres,
            flow=flow,
            at_boundary=is_boundary,
            boundary_faces=boundary_faces
        )
        LOG.info("Finished Import of " + os.path.realpath(folder))
        return vector_field

    @staticmethod
    def point_distance_to_plane(
            position: np.ndarray,
            face: 'pg.Face'
    ) -> float:
        # https://stackoverflow.com/questions/3860206/signed-distance-between-plane-and-point
        # Since position and face.normalized_normale can be assumed to be
        # 1D vectors (of length 3), we can assume the result of np.dot to be
        # a floating point value:
        return cast(
            float,
            np.dot(face.normalized_normal, position - face.position)
        )
