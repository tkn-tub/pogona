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

from typing import Optional, cast
import io
import os
import csv
import logging
import numpy as np

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class SensorFlowRate(pg.Component):
    """
    At the beginning of the simulation, the position of N sample points
    will be randomly set inside this sensor's Geometry.
    In each time step, the flow speed inside `attached_object` will be
    sampled and logged for each of these points.

    This class is intentionally not a subclass of the Sensor class,
    since child classes of Sensor have so far been reserved for sensors
    monitoring the positions of particles.
    (In its current implementation, the SensorManager considers all Sensor
    instances for sensor subscriptions, which we don't need for sampling
    the flow rate.)
    """

    translation = prop.VectorProperty([0, 0, 0], required=True)
    rotation = prop.VectorProperty([0, 0, 0], required=True)
    scale = prop.VectorProperty([1, 1, 1], required=True)
    shape = prop.EnumProperty(
        str(pg.Shapes.NONE.name),
        name='shape',
        required=True,
        enum_class=pg.Shapes,
    )
    """
    Shape of this sensor.
    Valid shapes are defined in the `pg.Shapes` enum.
    """
    log_folder = prop.StrProperty("sensor_data", required=False)
    """The file `sensor[<component name>].csv` will be created in here."""
    log_mesh_index = prop.BoolProperty(False, required=False)
    """
    If True, log the attached object's unique mesh index in each time step.
    """
    num_sample_points = prop.IntProperty(1, required=False)
    """
    The number of sample points N that will be added in addition
    to any sample points already defined in `sample_points`.
    """
    custom_sample_points_global = prop.ListOfVectorsProperty(
        [],
        required=False,
    )
    """
    Points to sample the flow rate at in every time step.
    Coordinates are in global coordinates.
    If `num_sample_points` is not 0, this list will be extended with
    randomly positioned points.
    """
    seed = prop.StrProperty('', required=False)
    """
    Seed for the pseudo-random number generator.
    If '', the random number generator of the simulation kernel
    will be used.
    If 'random', a random seed will be used for initialization.
    """
    attached_object = prop.ComponentReferenceProperty(
        '',
        required=True,
        can_be_empty=False,
    )
    """
    Component name of the object in which to sample the flow rate.
    """
    column_prefix = prop.StrProperty("flow_mps_", required=False)
    """
    Column header prefix for each sample point.

    By default, if `num_sample_points` is 2, for example, the output CSV
    may have the following columns:
    `[sim_time, flow_mps_[0 0 0]_x, flow_mps_[0 0 0]_y, flow_mps_[0 0 0]_z,
    flow_mps_[1 0 0]_x, flow_mps_[1 0 0]_y, flow_mps_[1 0 0]_z]`
    """

    def __init__(self):
        super().__init__()

        self._transformation = pg.Transformation()
        """Transformation of this sensor in the scene."""

        self._geometry = pg.Geometry(pg.Shapes.NONE)
        """Geometry of this sensor, set from shape."""

        self._attached_object: Optional['pg.Object'] = None
        self._csv_file: Optional[io.TextIOWrapper] = None
        self._csv_writer: Optional[csv.writer] = None
        self._rng = np.random.RandomState(seed=None)
        self._sample_points_global: Optional[np.ndarray] = None

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._geometry = pg.Geometry(shape=pg.Shapes[self.shape])

            self._transformation = pg.Transformation(
                translation=np.array(self.translation),
                rotation=np.array(self.rotation),
                scaling=np.array(self.scale)
            )

            if self.attached_object not in simulation_kernel.get_components():
                raise ValueError(
                    "No object component with the name "
                    f"{self.attached_object} attached to the simulation "
                    "kernel could be found."
                )

            if self.seed == 'random':
                self._rng = np.random.RandomState(seed=None)
            elif self.seed != '':
                self._rng = np.random.RandomState(seed=int(self.seed))
            else:
                self._rng = simulation_kernel.get_random_number_generator()

            self.initialize_sample_points()
        elif init_stage == pg.InitStages.CREATE_FOLDERS:
            os.makedirs(
                os.path.join(
                    simulation_kernel.results_dir,
                    self.log_folder
                ),
                exist_ok=True
            )
        elif init_stage == pg.InitStages.BUILD_SCENE:
            self._attached_object = cast(
                'pg.Object',
                simulation_kernel.get_components()[self.attached_object]
            )
        elif init_stage == pg.InitStages.CREATE_FILES:
            name = (
                self.id
                if self.component_name == "Generic component"
                else self.component_name
            )
            self._csv_file = open(
                os.path.join(
                    simulation_kernel.results_dir,
                    self.log_folder,
                    f'sensor[{name}].csv'
                ),
                mode='w'
            )
            fieldnames = ['sim_time']
            if self.log_mesh_index:
                fieldnames.append('mesh_index')
            # Assumes self.initialize_sample_points() to have been called:
            fieldnames.extend([
                # e.g., "my_prefix_[0.123, 42.0, 1.21]_x":
                f'{col}_{axis}' for col, axis in zip(
                    [
                        self.column_prefix + str(point_global)
                        for point_global in self._sample_points_global
                    ],
                    ['x', 'y', 'z']
                )
            ])
            self._csv_writer = csv.writer(
                self._csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )
            self._csv_writer.writerow(fieldnames)

    def initialize_sample_points(self):
        new_points_local = []
        if self._geometry.shape == pg.Shapes.POINT:
            new_points_local = np.zeros(self.num_sample_points, dtype=float)
        elif self._geometry.shape == pg.Shapes.CUBE:
            new_points_local = pg.util.get_random_points_in_cube_local(
                n=self.num_sample_points,
                rng=self._rng,
            )
        elif self._geometry.shape != pg.Shapes.NONE:
            new_points_local = pg.util.get_random_points_in_geometry_local(
                n=self.num_sample_points,
                geometry=self._geometry,
                rng=self._rng,
            )
        self._sample_points_global = self._transformation.apply_to_points(
            self.custom_sample_points_global + new_points_local
        )

    def finalize(self, simulation_kernel: 'pg.SimulationKernel'):
        self._csv_file.close()

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        csv_row = [simulation_kernel.sim_time]
        if self.log_mesh_index:
            csv_row.append(self._attached_object.get_mesh_index())
        vfm = self._attached_object.get_vector_field_manager()
        for sample_point_global in self._sample_points_global:
            csv_row.extend(vfm.get_flow_by_position(
                simulation_kernel=simulation_kernel,
                position_global=sample_point_global,
                interpolation_type=None,  # inherit from kernel
            ))
        self._csv_writer.writerow(csv_row)
