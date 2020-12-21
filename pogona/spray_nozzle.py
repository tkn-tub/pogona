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

import logging
import numpy as np

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SprayNozzle(pg.Component):
    translation = prop.VectorProperty([0, 0, 0], required=True)
    rotation = prop.VectorProperty([0, 0, 0], required=True)
    injection_amount = prop.IntProperty(100, required=True)
    velocity = prop.FloatProperty(1000, required=True)
    velocity_sigma = prop.FloatProperty(100, required=True)
    distribution_sigma = prop.FloatProperty(2.5, required=True)
    seed = prop.StrProperty('', required=False)
    """
    Seed for the pseudo-random number generator.
    If empty, the random number generator of the simulation kernel
    will be used.
    If 'random', a random seed will be used for initialization.
    Will be converted to int otherwise.
    """

    """
    A spray nozzle is an injector that "sprays" particles at a given position
    into a given direction.

    Usually an injector is controlled by an instance of
    ModulationOOK or a similar component, which determines when
    to switch the injector on or off and which also controls the flow
    speed in connected objects.
    """

    def __init__(self):
        super().__init__()
        self._turned_on = False
        self._burst_on = False
        self._rng = np.random.RandomState(seed=None)
        self._transformation = pg.Transformation()
        """Transformation of this sensor in the scene."""

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if self.seed == 'random':
                self._rng = np.random.RandomState(seed=None)
            elif self.seed != '':
                self._rng = np.random.RandomState(seed=int(self.seed))
            else:
                self._rng = simulation_kernel.get_random_number_generator()

            self._transformation = pg.Transformation(
                translation=np.array(self.translation),
                rotation=np.array(self.rotation),
                scaling=np.array([1, 1, 1])
            )

        elif init_stage == pg.InitStages.BUILD_SCENE:
            pass

    def turn_on(self):
        """
        Turn on the injector and start spawning particles.
        Usually called in the NotificationStages.MODULATION stage,
        so before SPAWNING in the current time step.

        :return:
        """
        # Start injecting molecules every time step
        LOG.debug("Injector turned on")
        self._turned_on = True

    def turn_off(self):
        """Stop injecting molecules"""
        LOG.debug("Injector turned off")
        self._turned_on = False

    def inject_burst(self):
        """Inject molecules in the next time step only"""
        LOG.debug("Injector bursts")
        self._burst_on = True

    def set_transformation(self, transformation: pg.Transformation):
        self._transformation = transformation

    def process_new_time_step(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.SPAWNING:
            return
        if self._turned_on or self._burst_on:
            # Only inject bursts once
            self._burst_on = False
            LOG.debug(f"Injecting {self.injection_amount} new molecules")

            base_delta_time = simulation_kernel.base_delta_time
            step_delta_time = base_delta_time / self.injection_amount
            delta_time = 0

            while delta_time < base_delta_time:
                # Spray one particle in positive y direction
                # with some randomness.

                used_velocity = (
                    self.velocity_sigma * self._rng.randn() + self.velocity
                )
                # Uniformly distributed angle between 0 and 2*pi by which
                # the new velocity vector will be roated around the y-axis:
                used_3d_angle = self._rng.random() * 2 * np.pi
                # Normally distributed angle by which the new velocity
                # vector will be rotated around the x- and z-axis:
                used_distribution = (
                    self.distribution_sigma * self._rng.randn() * (np.pi/180)
                )

                velocity_x = (
                    used_velocity
                    * np.sin(used_distribution)
                    * np.sin(used_3d_angle)
                )
                velocity_y = used_velocity * np.cos(used_distribution)
                velocity_z = (
                    used_velocity
                    * np.sin(used_distribution)
                    * np.cos(used_3d_angle)
                )

                velocity = self._transformation.apply_to_direction(
                    np.array((velocity_x, velocity_y, velocity_z))
                )
                position = self._transformation.apply_to_point(
                    np.array((0, 0, 0))
                )

                injected_molecule = pg.Molecule(
                    position + (velocity * delta_time),
                    velocity,
                    None,
                )
                simulation_kernel.get_molecule_manager().add_molecule(
                    injected_molecule
                )

                delta_time += step_delta_time
