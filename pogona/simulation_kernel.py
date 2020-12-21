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
from typing import Optional, Dict, Tuple
import logging
import itertools

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class SimulationKernel(pg.Component):
    """
    The simulation kernel that is responsible for starting and
    coordinating how a simulation is run.

    For configuration, kernel parameters are configured on the root level,
    along with the following 'kernel components':

    :molecule_manager:
        Configuration of the :class:`~pogona.MoleculeManager`
    :movement_predictor:
        Configuration of the :class:`~pogona.MovementPredictor`
    :scene_manager:
        Configuration of the :class:`~pogona.SceneManager`
    :sensor_manager:
        Configuration of the :class:`~pogona.SensorManager`
    :mesh_manager:
        Configuration of the :class:`~pogona.MeshManager`

    All other :class:`~pogona.Component` instances must be configured
    under the YAML key ``components``.
    """

    sim_time = prop.FloatProperty(0.0, required=False)
    sim_time_limit = prop.FloatProperty(0.0, required=True)
    seed = prop.IntProperty(1, required=True)
    results_dir = prop.StrProperty('', required=False)
    """Base directory for any result files (e.g., sensor logs)."""

    # Time step and step size control parameters
    # Fig. A.1 is a helpful flow chart:
    # https://web.archive.org/web/20191025090930/https://www.uni-muenster.de/imperia/md/content/physik_tp/lectures/ss2016/num_methods_ii/rkm.pdf
    base_delta_time = prop.FloatProperty(1.0, required=True)
    """
    Base time step for adaptive time stepping.
    Delta times will never be larger than this value.
    All logging and sensor evaluations happen at this interval.
    """
    adaptive_time_max_error_threshold = prop.FloatProperty(
        np.inf,
        required=False,
    )
    """
    If, when using adaptive time stepping, the error exceeds this
    threshold, the time step will be multiplied with
    time_step_reduction_factor and the molecule positions will be
    recalculated for the current step.
    """
    adaptive_time_safety_factor = prop.FloatProperty(0.85, required=False)
    """
    Safety factor for estimating the optimal next step size to keep
    the error below `adaptive_time_max_error_threshold`.
    We want to avoid picking a next step size that would cause us to
    just barely overshoot the error threshold in the next (sub-)step.
    """
    use_adaptive_time_stepping = prop.BoolProperty(False, required=False)
    """
    If True, use adaptive time stepping.
    Requires an appropriate integration method in the MovementPredictor.
    """
    adaptive_time_corrections_limit = prop.IntProperty(100, required=False)
    """
    Maximum number of corrections within one sub time step.
    Since we estimate the optimal sub step size, the number of
    corrections should usually be very low (< 10?).
    """
    interpolation_method = prop.EnumProperty(
        str(pg.Interpolation.MODIFIED_SHEPARD.name),
        name='interpolation_method',
        required=False,
        enum_class=pg.Interpolation,
    )

    def __init__(self):
        """
        """
        super().__init__()

        self._molecule_manager = pg.MoleculeManager()
        self._movement_predictor = pg.MovementPredictor()
        self._scene_manager = pg.SceneManager()
        self._sensor_manager = pg.SensorManager()
        self._mesh_manager = pg.MeshManager()
        self._kernel_components = dict(
            molecule_manager=self._molecule_manager,
            movement_predictor=self._movement_predictor,
            scene_manager=self._scene_manager,
            sensor_manager=self._sensor_manager,
            mesh_manager=self._mesh_manager,
        )
        for i, kernel_component in enumerate(self._kernel_components.values()):
            kernel_component.id = i
            # Ordinary components' IDs will be offset by the length
            # of the list of kernel components; see attach_component.
        self._components: Dict[str, 'pg.Component'] = dict()
        """
        A dictionary of all attached components by their respective component
        name.
        Being able to find components by a unique name is useful for components
        like the ModulationOOK, which has to find other components
        that are attached to it.
        """
        self._elapsed_base_time_steps = 0
        """Number of elapsed time steps (at *base_delta_time*!)"""
        self._elapsed_sub_time_steps = 0
        """Number of elapsed time steps, including all sub steps."""

        self._interpolation_method = pg.Interpolation.NEAREST_NEIGHBOR
        self._rng = np.random.RandomState(self.seed)

    def set_arguments(self, **kwargs):
        for kernel_component_name, kernel_component \
                in self._kernel_components.items():
            # (Pop kernel component sub-dictionaries from kwargs
            # such that the parent class method won't complain about
            # unrecognized arguments.)
            kernel_component.set_arguments(**kwargs.pop(
                kernel_component_name,
                dict()
            ))
        super().set_arguments(**kwargs)

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel=self, init_stage=init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._rng = np.random.RandomState(self.seed)
            self._interpolation_method = pg.Interpolation[
                self.interpolation_method]
            if (
                    self.use_adaptive_time_stepping
                    and self.adaptive_time_max_error_threshold == np.inf
            ):
                LOG.warning(
                    "`use_adaptive_time_stepping` is `True`, but "
                    "`adaptive_time_max_error_threshold` is not set."
                )

    def attach_component(self, component: 'pg.Component'):
        if component.component_name in self._components:
            raise ValueError(
                f"A component named {component.component_name} has already "
                f"been attached to the simulation kernel!"
            )
        if component.component_name in self._kernel_components:
            raise ValueError(
                f"\"{component.component_name}\" of the class "
                f"{component.__class__} is a kernel component and should "
                "not be added to the list of ordinary components."
            )
        component.id = len(self._components) + len(self._kernel_components)
        self._components[component.component_name] = component

    def notify_components_new_time_step(self):
        """
        Allow sensors and other components to process the new positions
        of molecules.
        If using adaptive time stepping,
        this is only called in base time steps!
        """
        for notification_stage in pg.NotificationStages:
            for component in self._components.values():
                component.process_new_time_step(
                    simulation_kernel=self,
                    notification_stage=notification_stage,
                )

    def initialize_components(self):
        """
        Run through all initialization stages for all attached
        components, starting with this simulation kernel itself,
        then the kernel components, and then the remaining components.

        Will be called automatically by the `start()` method.
        """
        for init_stage in pg.InitStages:
            LOG.info(f"running initialization stage {init_stage}")
            components = itertools.chain(
                [self],
                self._kernel_components.values(),
                self._components.values()
            )
            for component in components:
                component.initialize(self, init_stage)

    def start(self, skip_initialization=False):
        """
        Start the simulation.

        :param skip_initialization: Should only ever be True if you
            previously called initialize_components() yourself.
        """
        if not skip_initialization:
            LOG.info("Initializing components...")
            self.initialize_components()

        LOG.info("Starting simulation loop...")
        if not self.use_adaptive_time_stepping:
            self.simulation_loop_legacy()
        else:
            self.simulation_loop_adaptive_rkf()

        LOG.info("Finalizing...")
        for component in self._components.values():
            component.finalize(self)
        self.finalize(self)

    def simulation_loop_legacy(self):
        if self._molecule_manager.update_molecule_collection_immediately:
            raise ValueError(
                "`update_molecule_collection_immediately` should be set to "
                "False if using the default simulation loop (i.e., no "
                "adaptive time stepping)."
            )

        # Give all observers the chance to see the initial system at t=0
        LOG.debug("Initial simulation time " + str(self.sim_time))
        self.notify_components_new_time_step()
        while self.sim_time < self.sim_time_limit:
            # Use list() to copy the molecule dict keys because
            # _sensor_manager.process_molecule_moving may cause
            # molecules to be inserted/deleted.
            molecules = self._molecule_manager.get_all_molecules()
            for mid in self._molecule_manager.get_all_molecules().keys():
                molecule = molecules[mid]
                self._sensor_manager.process_molecule_moving_before(
                    self, molecule)
                updated_molecule, _, _ = self._movement_predictor.predict(
                    self,
                    molecule,
                    self.sim_time,
                    self.base_delta_time,
                )
                self._molecule_manager.update_molecule(updated_molecule)
                self._sensor_manager.process_molecule_moving_after(
                    self, updated_molecule)
            self._molecule_manager.apply_changes()
            self._elapsed_base_time_steps += 1
            self.sim_time = (
                self._elapsed_base_time_steps * self.base_delta_time
            )
            # self.sim_time = self.sim_time + self.sim_time_step_duration
            LOG.info(
                f"New simulation time {round(self.sim_time, 10)}"
            )
            self.notify_components_new_time_step()

    def simulation_loop_adaptive_rkf(self):
        """
        Simulation loop with adaptive time stepping.

        Uses a constant base time step `base_delta_time`.
        Within each base time step, sub-step sizes are chosen on a per-particle
        basis to ensure that the error of the selected
        Runge-Kutta-Fehlberg method (RKF) will stay below the threshold
        `adaptive_time_max_error_threshold`.

        Sensors are only notified in base time steps, for now.
        """
        if self._molecule_manager.update_molecule_collection_immediately:
            raise ValueError(
                "`update_molecule_collection_immediately` should be set to "
                "False in the MoleculeManager if using this variant of "
                "adaptive time stepping."
            )
            # TODO: double check; also: don't make users have to config this
        rkf_order = self._movement_predictor.embedded_integrator.order

        def _update_molecule(
                _molecule: 'pg.Molecule',
                _sub_sim_time: float,
        ) -> Tuple['pg.Molecule', float, int]:
            """
            Update a single molecule.
            First try with the latest recorded optimal time step.
            If the error threshold is exceeded, repeat with a smaller
            step size.

            :returns: The updated molecule, the most recently used
                step size, and the number of corrections.
            """
            _error = np.inf
            _dbg_errors = []

            _new_pos_global = _molecule.position  # will be overridden
            _delta_time = np.inf  # will be overridden
            _num_corrections = -1
            while (_error > self.adaptive_time_max_error_threshold and
                    _num_corrections <= self.adaptive_time_corrections_limit):
                _num_corrections += 1
                _delta_time = min(
                    # Take estimated optimal step size from prev. (sub-)step:
                    _molecule.delta_time_opt,  # may be np.inf
                    self.base_delta_time,
                    # Don't overshoot the base time step:
                    abs(self.base_delta_time - (_sub_sim_time - self.sim_time))
                )
                _, _new_pos_global, _error = self._movement_predictor.predict(
                    self,
                    _molecule,
                    _sub_sim_time,
                    delta_time=_delta_time,
                    update_molecule=False,  # we'll call update() manually
                )
                _dbg_errors.append(_error)
                # Determine an 'optimal' step size for the given threshold:
                if _error >= self.adaptive_time_max_error_threshold:
                    _exponent = 1 / (rkf_order + 1)
                else:
                    _exponent = 1 / rkf_order
                if _error == 0:
                    _molecule.delta_time_opt = np.inf
                else:
                    _molecule.delta_time_opt = (
                        self.adaptive_time_safety_factor
                        * _delta_time
                        * (self.adaptive_time_max_error_threshold / _error)
                        ** _exponent
                    )
            if _num_corrections > self.adaptive_time_corrections_limit:
                LOG.warning(
                    f"Maximum number of corrections limit exceeded for "
                    f"molecule {_molecule.id} at sub step time "
                    f"{_sub_sim_time} s, dt={_delta_time} s, {_dbg_errors=}"
                )
            _molecule.update(
                new_pos_global=_new_pos_global,
                scene_manager=self._scene_manager,
            )
            return molecule, _delta_time, _num_corrections

        def _advance_molecule_to_next_base_step(
                _molecule: 'pg.Molecule',
        ):
            _sim_time_next = self.sim_time + self.base_delta_time
            _sub_sim_time = self.sim_time
            _num_steps = 0
            _num_corrections_m_total = 0
            while (
                    _sub_sim_time < _sim_time_next
                    and not np.isclose(  # ensure 'strictly less than'
                        _sub_sim_time,
                        _sim_time_next,
                        rtol=1e-10,
                        atol=1e-15,
                    )
            ):
                _num_steps += 1
                _, _delta_time, _num_corrections_u = _update_molecule(
                    _molecule=_molecule,  # will be updated in-place
                    _sub_sim_time=_sub_sim_time,
                )
                # ^ Takes care to not overshoot base steps;
                #  _delta_time will be made just small enough.
                _num_corrections_m_total += _num_corrections_u
                _sub_sim_time += _delta_time
            return _molecule, _num_steps, _num_corrections_m_total

        # Give all observers the chance to see the initial system at t=0
        LOG.debug("Initial simulation time " + str(self.sim_time))
        self.notify_components_new_time_step()
        while self.sim_time < self.sim_time_limit:
            molecules = self._molecule_manager.get_all_molecules()

            num_steps = []
            num_corrections = []
            for molecule in molecules.values():
                self._sensor_manager.process_molecule_moving_before(
                    simulation_kernel=self,
                    molecule=molecule,
                )  # mainly for updating SensorTeleporting
                _, num_steps_m, num_corrections_m = (
                    _advance_molecule_to_next_base_step(
                        _molecule=molecule,
                    )
                )
                num_steps.append(num_steps_m)
                num_corrections.append(num_corrections_m)
                self._sensor_manager.process_molecule_moving_after(
                    simulation_kernel=self,
                    molecule=molecule
                )  # update all remaining sensors
            self._molecule_manager.apply_changes()

            # LOG.debug(
            #     f"t={self.sim_time}: "
            #     f"{len(molecules)} molecules, "
            #     f"mean_max_error={np.mean(errors)}, "
            #     f"min_max_error={np.min(errors)}, "
            #     f"max_max_error={np.max(errors)}, "
            #     f"mean_steps={np.mean(num_steps)}, "
            #     f"min_steps={np.min(num_steps)}, "
            #     f"max_steps={np.max(num_steps)}"
            # )

            self._elapsed_base_time_steps += 1
            self.sim_time = (
                self._elapsed_base_time_steps * self.base_delta_time
            )
            LOG.info(
                f"New (base-step) simulation time {round(self.sim_time, 10)}"
            )
            self.notify_components_new_time_step()

    def destroy_molecule(self, molecule):
        self._molecule_manager.destroy_molecule(molecule)

    def get_components(self) -> Dict[str, 'pg.Component']:
        return self._components

    def get_molecule_manager(self) -> 'pg.MoleculeManager':
        return self._molecule_manager

    def get_movement_predictor(self) -> 'pg.MovementPredictor':
        return self._movement_predictor

    def get_scene_manager(self) -> 'pg.SceneManager':
        return self._scene_manager

    def get_sensor_manager(self) -> 'pg.SensorManager':
        return self._sensor_manager

    def get_mesh_manager(self) -> 'pg.MeshManager':
        return self._mesh_manager

    def get_simulation_time(self) -> float:
        return self.sim_time

    def get_elapsed_base_time_steps(self) -> int:
        return self._elapsed_base_time_steps

    def get_elapsed_sub_time_steps(self) -> int:
        return self._elapsed_sub_time_steps

    def get_base_delta_time(self) -> float:
        return self.base_delta_time

    def get_random_number_generator(self) -> np.random.RandomState:
        return self._rng

    def get_seed(self) -> Optional[int]:
        return self.seed

    def get_interpolation_method(self) -> 'pg.Interpolation':
        return self._interpolation_method

    def get_integration_method(self) -> 'pg.Integration':
        return self._movement_predictor.get_integration_method()
