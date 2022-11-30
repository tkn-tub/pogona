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

from typing import List
import logging
import enum
import numpy as np

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SensorSubscriptionsUsage(enum.Enum):
    ENABLED = 1
    DISABLED = 2
    USE_DEFAULT = 3


class SensorManager(pg.Component):
    default_use_sensor_subscriptions = prop.BoolProperty(True, required=False)
    """
    Notify subscribed sensors based on object mesh cells.
    This speeds up simulation.
    Only disable this if you are constrained by memory.
    Individual objects can override this setting.
    """
    use_range_queries = prop.BoolProperty(True, required=False)
    """
    When determining possible sensor subscriptions, execute range
    queries on the Object's k-d tree instead of iterating the
    entire mesh.
    Use this if all sensors occupy a relatively small volume compared
    to each mesh.
    Performance may degrade for large sensors.
    """
    component_name = prop.StrProperty("sensor_manager", required=False)
    """Since this component is not created by the config, choose a name"""

    def __init__(self):
        super().__init__()
        self._sensors: List[pg.Sensor] = []
        self._sensor_subscriptions: List[List[List[int]]] = []
        """Indexable by object ID, cell ID; holds a list of sensor IDs"""

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CREATE_SENSOR_SUBSCRIPTIONS:
            # Initialize the subscription array
            for i, obj in enumerate(
                    simulation_kernel.get_scene_manager().get_all_objects()):
                if obj.object_id != len(self._sensor_subscriptions):
                    raise AssertionError(
                        "Creating the sensor subscription array failed "
                        f"because the ID of object \"{obj.component_name}\" "
                        f"= {obj.object_id}, which has index {i} in the list "
                        "of objects, does not match the length of the "
                        "list of sensor subscriptions "
                        f"= {len(self._sensor_subscriptions)}. "
                        "Maybe it was somehow attached twice?"
                    )

                # Ensure that there is a mesh to add subscriptions to,
                # even if the object is inactive:
                fallback_mesh_index = obj.get_fallback_mesh_index()
                if not obj.is_active and fallback_mesh_index is not None:
                    # Try to temporarily load a fallback mesh, if it exists.
                    LOG.debug(
                        "Ensure that a mesh exists even if object is "
                        "inactive by loading a fallback mesh for "
                        f"object \"{obj.component_name}\". "
                        f"{fallback_mesh_index=}"
                    )
                    vector_field = (
                        simulation_kernel.get_mesh_manager().load_vector_field(
                            openfoam_sim_path=obj.get_path(fallback=True),
                            mesh_index=fallback_mesh_index,
                            walls_patch_names=obj.walls_patch_names,
                            dummy_boundary_points=obj.dummy_boundary_points,
                        )
                    )
                    vfm = pg.VectorFieldManager(
                        vector_field=vector_field,
                        transformation=obj.get_transformation()
                    )
                    mesh_global = vfm.get_cell_centres_global()
                else:
                    # Object is likely active, or it doesn't support
                    # subscriptions.
                    # In the latter case, mesh_global will be None.
                    mesh_global = obj.get_current_mesh_global()

                if (mesh_global is None
                        or not self._uses_sensor_subscriptions(obj)):
                    # The object does not support subscriptions.
                    self._sensor_subscriptions.append([])
                else:
                    # Ensure that for every mesh cell,
                    # we have an array of subscriptions ready
                    self._sensor_subscriptions.append(
                        [[] for _ in range(len(mesh_global))])

                    # Write subscriptions to the array
                    for sensor in self._sensors:
                        if self.use_range_queries:
                            # Use k-d tree range queries to determine possible
                            #   cells
                            cell_ids = self._get_mesh_subset_ids(
                                obj,
                                sensor)
                            LOG.debug(
                                f"Range query subset of size "
                                f"{len(cell_ids)}. "
                                f"Original size: {len(mesh_global)} "
                                f"while subscribing sensor "
                                f"\"{sensor.component_name}\" to object "
                                f"\"{obj.component_name}\"."
                            )
                        else:
                            # Just ask for all cell ids
                            cell_ids = [[] for _ in range(len(mesh_global))]

                        for cell_id in cell_ids:
                            cell_centre = mesh_global[cell_id]
                            if sensor.is_inside_sensor_zone(cell_centre):
                                self._sensor_subscriptions[obj.object_id][
                                    cell_id].append(sensor.sensor_id)

    def register_sensor(
            self,
            sensor: 'pg.Sensor'
    ):
        """
        :param sensor:
        :return: nothing
        """
        sensor.sensor_id = len(self._sensors)
        self._sensors.append(sensor)
        LOG.debug(f"Registered new sensor \"{sensor.component_name}\"")

    def _uses_sensor_subscriptions(self, obj: 'pg.Object'):
        """
        :return: True iff obj is supposed to use sensor subscriptions.
            obj.use_sensor_subscriptions has precedence over
            self.default_use_sensor_subscriptions.
        """
        return obj.is_active and (
            (
                obj.use_sensor_subscriptions
                == pg.SensorSubscriptionsUsage.USE_DEFAULT
                and self.default_use_sensor_subscriptions
            ) or (
                obj.use_sensor_subscriptions
                == pg.SensorSubscriptionsUsage.ENABLED
            )
        )

    def _get_mesh_subset_ids(self, obj: "pg.Object", sensor: 'pg.Sensor'):
        # Query radius: All shapes are confined to a box with
        #   side lengths 1 centered around (0, 0, 0).
        #   Use the distance to one of the corners of this box
        #   as the radius:
        radius = np.sqrt(
            (sensor.transformation.scaling[0] / 2) ** 2
            + (sensor.transformation.scaling[1] / 2) ** 2
            + (sensor.transformation.scaling[2] / 2) ** 2
        )
        return obj.get_vector_field_manager().kd_tree_global.query_ball_point(
            # Center point of this sensor:
            x=sensor.transformation.translation,
            # Query radius:
            r=radius
        )

    def _get_subscribed_sensors(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        molecule: 'pg.Molecule',
    ):
        """
        :param simulation_kernel:
        :param molecule:
        :return: List of sensors subscribed to the current cell of the given
        molecule if sensor subscriptions are active, otherwise returns the
        list of all sensors.
        """
        # Just use all sensors if there is no related object_id
        if molecule.object_id is None:
            return self._sensors

        obj = simulation_kernel.get_scene_manager().get_all_objects()[
            molecule.object_id]
        if self._uses_sensor_subscriptions(obj) and len(
                self._sensor_subscriptions[molecule.object_id]) > 0:
            # Find out which sensors are subscribed to this particular cell
            subscribed_sensor_ids = (
                self._sensor_subscriptions[molecule.object_id][
                    molecule.cell_id]
            )
            return [
                self._sensors[sensor_id]
                for sensor_id in subscribed_sensor_ids
            ]
        else:
            # Just notify all sensors.
            # Either we do not want to use sensor subscriptions at all,
            #   or the object in which the molecule is does not provide a mesh.
            return self._sensors

    def process_molecule_moving_before(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule',
    ):
        """
        Called before updating the position of a particle within a time step.
        Useful for SensorTeleporting, for example, which should consider
        the position of particles right after they have been spawned.

        :param simulation_kernel:
        :param molecule:
        :return:
        """
        subscribed_sensors = self._get_subscribed_sensors(
            simulation_kernel=simulation_kernel,
            molecule=molecule,
        )
        for sensor in subscribed_sensors:
            sensor.process_molecule_moving_before(
                simulation_kernel=simulation_kernel,
                molecule=molecule,
            )

    def process_molecule_moving_after(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule',
    ):
        """
        Called after the position of a particle has been updated.
        Useful for updating regular sensors.

        :param simulation_kernel:
        :param molecule:
        :return:
        """
        subscribed_sensors = self._get_subscribed_sensors(
            simulation_kernel=simulation_kernel,
            molecule=molecule,
        )
        for sensor in subscribed_sensors:
            sensor.process_molecule_moving_after(
                simulation_kernel=simulation_kernel,
                molecule=molecule,
            )
