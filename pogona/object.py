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

from abc import ABCMeta, abstractmethod
from typing import List, Optional, Set
import os
import re
import numpy as np
import logging

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class Object(pg.Component, metaclass=ABCMeta):
    object_id = prop.IntProperty(-1, required=False)
    """Object index, set by the scene manager."""
    # TODO: hide from user

    translation = prop.VectorProperty([0, 0, 0], required=True)
    rotation = prop.VectorProperty([0, 0, 0], required=True)
    scale = prop.VectorProperty([1, 1, 1], required=True)
    openfoam_cases_path = prop.StrProperty("", required=True)
    """
    Path to all OpenFOAM simulation cases.
    Subclasses may use this as the base path to find their respective
    meshes via `get_path()`.
    """
    use_sensor_subscriptions = prop.EnumProperty(
        str(pg.SensorSubscriptionsUsage.USE_DEFAULT.name),
        name='use_sensor_subscriptions',
        required=False,
        enum_class=pg.SensorSubscriptionsUsage,
    )
    """
    Notify subscribed sensors based on object mesh cells.
    This speeds up simulation.
    Only disable this if you are constrained by memory or if the object
    does not have a mesh in the first place.
    If None, use the SensorManager's default_use_sensor_subscriptions.
    """
    dummy_boundary_points = prop.EnumProperty(
        str(pg.DummyBoundaryPointsVariant.NONE.name),
        name='dummy_boundary_points',
        required=False,
        enum_class=pg.DummyBoundaryPointsVariant,
    )
    """
    Whether to insert dummy points at the boundary of the mesh,
    and where exactly.
    This may help with interpolation.
    """

    def __init__(self):
        super().__init__()

        self._vector_field_manager: Optional['pg.VectorFieldManager'] = None
        """This object's VectorFieldManager, set by child classes."""
        self._walls_patch_names: Set[str] = {
            'walls',
            'yConnectorPatch',
            'tubePatch'
        }
        """
        A superset of names of wall patches.
        Required by the VectorFieldParser:
            "Which patches to consider as boundaries
            (typically does not include inlets and outlets)."
        """
        self._transformation: Optional['pg.Transformation'] = None
        """
        Transformation of this object in the scene.
        """
        self.inlets: List[str] = []
        """Names of the inlets in the OpenFOAM mesh."""
        self.outlets: List[str] = []
        """Names of the outlets in the OpenFOAM mesh."""
        self.name: str = "Generic Object"
        """
        The name of this type of object.
        Not a unique identifier like Component.component_name!
        """

        self._is_active = True
        """
        If True, indicates that fluid inside this Object is moving.
        """
        self._default_time_str: str = "latest"
        """
        Default sub-folder of the OpenFOAM simulation results to use.
        If "latest", will search for the sub-folder which name is a
        floating point number and has the greatest value.
        """

        self._ignored_arguments.update({
            # These arguments are passed to all components present in the
            # scene. A (mesh) object won't need them, but we also don't
            # want to see warnings if these arguments are passed anyway:
            'geometry',
            'shape',
            'visualization_scale',
        })

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._transformation = pg.Transformation(
                translation=np.array(self.translation),
                rotation=np.array(self.rotation),
                scaling=np.array(self.scale)
            )
        if init_stage == pg.InitStages.CREATE_DATA_STRUCTURES:
            self.load_current_vector_field(simulation_kernel)
        if init_stage == pg.InitStages.BUILD_SCENE:
            simulation_kernel.get_scene_manager().add_object(self)

    @property
    @abstractmethod
    def _openfoam_cases_subpath(self):
        """
        In which folder of `openfoam_cases_path` to find the cases for this
        Object class.
        `get_path()` will be relative to
        `<openfoam_cases_path>/<openfoam_cases_subpath>`.
        """
        pass

    @property
    def is_active(self):
        return self._is_active

    @property
    def walls_patch_names(self):
        return self._walls_patch_names

    def get_transformation(self) -> 'pg.Transformation':
        return self._transformation

    def get_vector_field_manager(self) -> Optional['pg.VectorFieldManager']:
        if not self._is_active:
            return None
        return self._vector_field_manager

    def get_current_mesh_local(self) -> Optional[np.ndarray]:
        if not self._is_active:
            return None
        return self._vector_field_manager.get_cell_centres_local()

    def get_current_mesh_global(self) -> Optional[np.ndarray]:
        if not self._is_active:
            return None
        return self._vector_field_manager.get_cell_centres_global()

    def get_closest_cell_centre_id(
            self,
            position_global: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        :returns: Array of closest cell centers to `position`.
            If there's only one position, output is squeezed.
            None if this Object is inactive.
            See documentation of cKDTree.query().
        """
        if not self.is_active:
            return None
        return self._vector_field_manager.get_closest_cell_centre_id(
            position_global=position_global
        )

    def get_flow(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            position_global: np.ndarray,
            sim_time: float
    ):
        if not self._is_active:
            return np.array([0, 0, 0], dtype=np.float)
        return self._vector_field_manager.get_flow_by_position(
            simulation_kernel=simulation_kernel,
            position_global=position_global
        )

    def load_current_vector_field(
            self,
            simulation_kernel: 'pg.SimulationKernel'
    ):
        if not self._is_active:
            # This saves us the extra step of having to load a mesh
            # with all 0s.
            return
        old_mesh_size = (
            len(self._vector_field_manager.get_mesh())
            if self._vector_field_manager is not None
            else None
        )
        vector_field = simulation_kernel.get_mesh_manager().load_vector_field(
            openfoam_sim_path=self.get_path(),
            mesh_index=self.get_mesh_index(),
            walls_patch_names=self._walls_patch_names,
            dummy_boundary_points=pg.DummyBoundaryPointsVariant[
                self.dummy_boundary_points],
        )
        new_mesh_size = (
            len(self._vector_field_manager.get_mesh())
            if self._vector_field_manager is not None
            else None
        )
        if (old_mesh_size is not None
                and new_mesh_size is not None
                and old_mesh_size != new_mesh_size):
            # Comparison will only apply to states of this Object in which
            # self._is_active was True.
            raise AssertionError(
                f"Object {self.name} loaded a new vector field, "
                f"but the new mesh ({new_mesh_size} cells) doesn't match "
                f"the old one ({old_mesh_size} cells)."
            )
        self._vector_field_manager = pg.VectorFieldManager(
            vector_field=vector_field,
            transformation=self._transformation
        )

    @abstractmethod
    def get_mesh_index(self) -> str:
        """
        :returns: A unique string for the current configuration of this object.
            Used for caching.
        """
        pass

    @abstractmethod
    def get_fallback_mesh_index(self) -> Optional[str]:
        """
        If an Object supports sensor subscriptions, some OpenFOAM case
        with a non-zero flow rate should exist (i.e., a vector field for
        which this Object has `self.is_active == True`).
        If this object is initially inactive, however, we still need to know
        where to find this mesh for the initialization of the
        SensorManager.

        :returns: A valid mesh index independent of this Object's
            `is_active` status.
            None if this Object does not support sensor subscriptions.
        """
        pass

    def get_path(self, use_latest_time_step=False, fallback=False) -> str:
        """
        :param use_latest_time_step: Find the latest time step in path.
            If False, use this Object's `_default_time_str`,
            which may still be set to 'latest', which has the same effect.
        :param fallback: Use `get_fallback_mesh_index` instead of
            `get_mesh_index`.
        :return: Path to the OpenFOAM files for this object.
        """
        """
        :param use_latest_time_step: Find the latest time step in path
        :return: Path to the OpenFOAM files for this object.
        """
        if not self._is_active:
            return ''
        mesh_index = (
            self.get_mesh_index() if not fallback
            else self.get_fallback_mesh_index()
        )
        if fallback and mesh_index is None:
            raise ValueError(
                "Tried to call `get_path` with the fallback flag enabled, "
                "but this Object does not have a fallback mesh index."
            )

        path = os.path.join(
            self.openfoam_cases_path,
            self._openfoam_cases_subpath,
            mesh_index
        )

        if use_latest_time_step or self._default_time_str == 'latest':
            return os.path.join(path, self.find_latest_time_step(path))
        return os.path.join(path, self._default_time_str)

    @abstractmethod
    def process_changed_inlet_flow_rate(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        inlet_name: str,
        flow_rate: float
    ):
        """
        Update the flow rate inside this Object based on the changed flow
        rate of the inlet with name `inlet_name`,
        then propagate this change to any Object connected to this Object's
        outlets.

        Should also update `is_active` accordingly.
        """
        pass

    @abstractmethod
    def get_outlet_area(self, outlet_name: str) -> (
            'pg.Geometry',
            'pg.Transformation'
    ):
        pass

    @staticmethod
    def find_latest_time_step(path: str) -> str:
        """
        :return: The highest-valued subdirectory of path that is named
            only after a floating point value.
            E.g., if there are '{path}/0/' and '{path}/0.1/', this will return
            '0.1'.
        """
        # Float pattern from
        # https://docs.python.org/3/library/re.html#simulating-scanf:
        p = re.compile(r'^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$')
        all_files_and_dirs = os.listdir(path)
        matching_files_and_dirs = [f for f in all_files_and_dirs if p.match(f)]
        if len(matching_files_and_dirs) == 0:
            raise ValueError(
                f"Could not find a subfolder for the latest time step "
                f"in \"{path}\"."
            )
        return max(matching_files_and_dirs, key=lambda x: float(x))
