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
import pogona.properties as prop
import logging

import numpy as np
from typing import Optional, List, cast


LOG = logging.getLogger(__name__)


class Injector(pg.Component):
    """
    An injector spawns particles within its defined volume in every time
    step in which it is turned on.

    Usually an injector is controlled by an instance of
    ModulationOOK or a similar component, which determines when
    to switch the injector on or off and which also controls the flow
    speed in connected objects.
    """
    shape = prop.EnumProperty(
        default='NONE',
        name='shape',
        required=True,
        enum_class=pg.Shapes,
    )
    """
    Shape of this injector.
    Valid shapes are defined in the `pg.Shapes` enum.
    """
    translation = prop.VectorProperty([0, 0, 0], required=True)
    rotation = prop.VectorProperty([0, 0, 0], required=True)
    scale = prop.VectorProperty([1, 1, 1], required=True)
    attached_object = prop.ComponentReferenceProperty(
        "",
        required=False,
        can_be_empty=True,
    )
    """
    Component name of the attached object.
    This has to be set if you want newly spawned particles to be influenced
    by a vector field!
    """
    injection_amount = prop.IntProperty(0, required=False)
    """
    *Number* of molecules spawned in every
    time step while the injector is active.
    """
    seed = prop.StrProperty('', required=False)
    """
    Seed for the pseudo-random number generator.
    If empty, the random number generator of the simulation kernel
    will be used.
    If 'random', a random seed will be used for initialization.
    Will be converted to int otherwise.
    """

    def __init__(self):
        super().__init__()
        self._attached_object: Optional['pg.Object'] = None
        self._turned_on = False
        self._burst_on = False
        self._rng = np.random.RandomState(seed=None)
        self._geometry: Optional['pg.Geometry'] = None
        """Geometry of this injector."""
        self._transformation: Optional['pg.Transformation'] = None
        """Transformation of this injector in the scene."""

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

            self._geometry = pg.Geometry(shape=pg.Shapes[self.shape])
            self._transformation = pg.Transformation(
                translation=np.array(self.translation),
                rotation=np.array(self.rotation),
                scaling=np.array(self.scale)
            )

            if (self.attached_object != ''
                    and self.attached_object
                    not in simulation_kernel.get_components()):
                raise ValueError(
                    "No object component with the name "
                    f"{self.attached_object} attached to the simulation "
                    "kernel could be found."
                )
        elif init_stage == pg.InitStages.BUILD_SCENE:
            self._attached_object = cast(
                'pg.Object',
                simulation_kernel.get_components()[self.attached_object]
            )

    def turn_on(self):
        """
        Turn on the injector and start spawning particles.
        Usually called in the NotificationStages.MODULATION stage,
        so before SPAWNING in the current time step.

        :return:
        """
        # Start injecting molecules every time step
        self._turned_on = True

    def turn_off(self):
        # Stop injecting molecules
        self._turned_on = False

    def inject_burst(self):
        # Inject molecules in the next time step only
        self._burst_on = True

    def set_geometry(self, geometry: pg.Geometry):
        self._geometry = geometry

    def set_transformation(self, transformation: pg.Transformation):
        self._transformation = transformation

    def generate_points_local(self) -> List[np.ndarray]:
        return [np.array((0, 0, 0)) for _ in range(self.injection_amount)]

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
            if self._geometry.shape == pg.Shapes.POINT:
                points_local = self.generate_points_local()
            elif self._geometry.shape == pg.Shapes.CUBE:
                points_local = pg.util.get_random_points_in_cube_local(
                    n=self.injection_amount,
                    rng=self._rng,
                )
            else:
                points_local = pg.util.get_random_points_in_geometry_local(
                    n=self.injection_amount,
                    geometry=self._geometry,
                    rng=self._rng,
                )

            new_points_global = self._transformation.apply_to_points(
                points_local
            )
            # TODO: transformation should probably be applied earlier!
            #  see issue #160

            for new_point_global in new_points_global:
                injected_molecule = pg.Molecule(
                    position=new_point_global,
                    velocity=np.zeros(3),
                    object_id=self._attached_object.object_id,
                )
                simulation_kernel.get_molecule_manager().add_molecule(
                    injected_molecule
                )
