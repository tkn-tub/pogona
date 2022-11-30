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

from typing import Set
import os
import pickle
from pickle import PickleError
import logging
import re

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class MeshManager(pg.Component):
    cache_path = prop.StrProperty("", required=False)
    """
    Directory for cached objects.
    (Not relative to the results folder.)

    By default, this will be set to `<OpenFOAM cases path>/cache`.
    """
    openfoam_cases_path = prop.StrProperty("", required=True)
    """
    Path to MaMoKo OpenFOAM cases.
    Usually this is passed to the individual objects directly.
    In the MeshManager, this path is only used as a default prefix
    for cache_path if cache_path is not set explicitly.
    """

    def __init__(
        self
    ):
        super().__init__()

        self._parsed_meshes = dict()

    def initialize(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            LOG.debug(f"{self.openfoam_cases_path=}")
            if 'cache_path' not in self._arguments_already_set:
                self.cache_path = os.path.join(
                    self.openfoam_cases_path,
                    'cache'
                )

    @staticmethod
    def get_valid_filename(s):
        """
        Copied from the Django project's django.utils.text:
        https://github.com/django/django/blob/master/django/utils/text.py

        Return the given string converted to a string that can be used for a
        clean filename. Remove leading and trailing spaces; convert other
        spaces to underscores; and remove anything that is not an alphanumeric,
        dash, underscore, or dot.
        >>> MeshManager.get_valid_filename("john's portrait in 2004.jpg")
        'johns_portrait_in_2004.jpg'
        """
        s = str(s).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', s)

    @staticmethod
    def _get_mesh_string_from_path(openfoam_sim_path: str):
        """
        Generate an identifier string for a mesh from the path to its
        OpenFOAM simulation files.

        :param openfoam_sim_path:
        :return:
        """
        path_stripped = openfoam_sim_path.strip('/\\')
        # Splitting by slashes, might not work on Windows:
        path_components = path_stripped.split('/')
        # Using only the 3 lowest directories for the mesh string.
        # E.g., "/path/to/openfoam/files/tube/42cm_33lps/0.9"
        # would result in the mesh string "tube__42cm_33lps__0.9".
        return '__'.join(path_components[-3:])

    def save_cached_vector_field(
            self,
            mesh_string,
            vector_field: 'pg.VectorField'):
        LOG.info(f"Saving mesh file \"{mesh_string}\" to cache.")
        file_name = self.get_file_name_for_cached_mesh(mesh_string)
        path = os.path.dirname(file_name)
        os.makedirs(path, exist_ok=True)
        pickle.dump(vector_field, open(file_name, "wb"))
        LOG.info(
            f"Saved mesh cache file \"{mesh_string}\" in \"{file_name}\"."
        )

    def load_vector_field(
        self,
        openfoam_sim_path: str,
        mesh_index: str = None,
        walls_patch_names: Set[str] = None,
        dummy_boundary_points: str = None,
    ) -> 'pg.VectorField':
        """

        :param openfoam_sim_path: Path to the OpenFOAM simulation
            result (the directory for one specific time step) for the
            vector field to load.
        :param mesh_index: A unique string for the OpenFOAM simulation case
            and mesh given by openfoam_sim_path.
            Will be converted internally using
            `MeshManager.get_valid_filename`.
            If None, a mesh index will be generated from openfoam_sim_path.
        :param walls_patch_names: Which patches to consider as boundaries
            (typically does not include inlets and outlets).
        :param dummy_boundary_points: 'face-centers', 'face-points', or
            'none'/None (default).  TODO: enum?
        :return: The cached vector field, if it exists. Otherwise the
            vector field will be loaded from the given path.
        """
        if openfoam_sim_path == "":
            raise ValueError("openfoam_sim_path must not be empty")
        if mesh_index is not None:
            mesh_string = self.get_valid_filename(mesh_index)
        else:
            mesh_string = self._get_mesh_string_from_path(openfoam_sim_path)

        vector_field = None
        if mesh_string in self._parsed_meshes:
            # We already loaded the vector field, use the one in memory
            vector_field = self._parsed_meshes[mesh_string]

        if vector_field is None:
            # Try loading a pickled version
            file_name = self.get_file_name_for_cached_mesh(mesh_string)
            LOG.info("Loading cached mesh file " + os.path.realpath(file_name))
            try:
                file = open(file_name, "rb")
                vector_field = pickle.load(file)
            except PickleError:
                LOG.warning(
                    "I cannot unpickle the cached mesh file "
                    f"\"{os.path.realpath(file_name)}\". "
                    "Reloading mesh from simulation results…"
                )
            except IOError or FileNotFoundError:
                LOG.info(
                    f"Cached file not found for mesh \"{mesh_string}\". "
                    "Reloading mesh from simulation results…"
                )

        if vector_field is None:
            # Parse file
            vector_field = self.parse_mesh(
                import_folder=openfoam_sim_path,
                mesh_string=mesh_string,
                walls_patch_names=walls_patch_names,
                dummy_boundary_points=dummy_boundary_points,
            )

        # Save vector field to memory for future use
        self._parsed_meshes[mesh_string] = vector_field
        # TODO(jdrees): Find out whether copying might be necessary
        # return copy.deepcopy(vector_field)
        LOG.info(f"Finished loading mesh file \"{mesh_string}\".")
        return vector_field

    def get_file_name_for_cached_mesh(self, mesh_string: str):
        return os.path.join(
            self.cache_path,
            mesh_string + ".pickle"
        )

    def parse_mesh(
        self,
        import_folder: str,
        mesh_string: str,
        walls_patch_names: Set[str] = None,
        dummy_boundary_points: str = None,
    ) -> 'pg.VectorField':
        # Check if folder exists
        if not os.path.isdir(import_folder):
            LOG.critical(
                "The openfoam simulation result folder "
                f"\"{import_folder}\" is not a directory. "
                "Are you sure you ran the openfoam simulation and put the "
                "result in the correct directory?"
            )
            exit(1)
        vector_field = pg.VectorFieldParser.parse_folder(
            folder=import_folder,
            walls_patch_names=walls_patch_names,
            dummy_boundary_points=dummy_boundary_points,
        )
        self.save_cached_vector_field(mesh_string, vector_field)
        return vector_field
