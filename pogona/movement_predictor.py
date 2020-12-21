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
from typing import Tuple, Callable, Any, Optional
import logging
import abc

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class EmbeddedRungeKuttaMethod(abc.ABC):
    """
    Butcher tableau for a specific Runge-Kutta method as defined here:
    https://web.archive.org/save/https://en.wikipedia.org/wiki/List_of_Runge–Kutta_methods
    """
    A: np.ndarray
    """A square matrix."""
    B: np.ndarray
    """
    'Horizontal header', starting from the left,
    2 rows where the first row should give the higher-order accuracy solution.
    """
    C: np.ndarray  # "vertical header", starting at the top
    """A 1D matrix, 'vertical header'"""

    def compute(
            self,
            func: Callable[[float, Any], Any],
            t_old: float,
            y_old: Any,
            dt: float,
    ) -> Tuple[Any, Any, Any]:
        """
        :param func: A function mapping a time t and value y to
            a time derivative of y (dy/dt).
        :param t_old: Time of the previous time step.
        :param y_old: Value at t_old.
        :param dt: delta time.
        :return: The predicted new value with highest-order accuracy,
            the predicted new value with lower-order accuracy,
            and the difference (error) between the two.
        """
        s = 0
        s_low = 0
        k = []
        for i in range(len(self.C)):
            # sum from j=1 to i-1 over a_ij * k_j:
            # (reshape and transpose to make element-wise multiplication
            # with k possible, which could be a list of Vector3)
            sum_ak = (self.A[i][:i].reshape(1, i).T * k).sum()
            # k_i = f(t_n + c_i * h_i, y_n + dt * sum_ak):
            k.append(func(
                t_old + self.C[i] * dt,
                y_old + dt * sum_ak
            ))
            s += self.B[0][i] * k[-1]
            s_low += self.B[1][i] * k[-1]
        y_next = y_old + dt * s
        y_next_low = y_old + dt * s_low
        error = y_next - y_next_low

        return y_next, y_next_low, error

    @property
    @abc.abstractmethod
    def order(self):
        """
        The order of the higher-order method used for the actual
        integration.
        """
        return 0


class RKFehlberg45(EmbeddedRungeKuttaMethod):
    """DOI: 10.1007/BF02241732"""
    A = np.array([
        [0,         0,          0,          0,         0,      0],
        [1/4,       0,          0,          0,         0,      0],
        [3/32,      9/32,       0,          0,         0,      0],
        [1932/2197, -7200/2197, 7296/2197,  0,         0,      0],
        [439/216,   -8,         3680/513,   -845/4104, 0,      0],
        [-8/27,     2,          -3544/2565, 1859/4104, -11/40, 0],
    ])
    B = np.array([
        [16/135, 0, 6656/12825, 28561/56430, -9/50, 2/55],
        [25/216, 0, 1408/2565,  2197/4104,   -1/5,  0]
    ])
    C = np.array([0, 1/4, 3/8, 12/13, 1, 1/2])

    @property
    def order(self):
        return 5


class MovementPredictor(pg.Component):
    component_name = prop.StrProperty('movement_predictor', required=False)
    integration_method = prop.EnumProperty(
        default=str(pg.Integration.RUNGE_KUTTA_4.name),
        name='integration_method',
        required=True,
        enum_class=pg.Integration,
    )

    def __init__(self):
        super().__init__()

        self._integration_method = pg.Integration[self.integration_method]
        self._embedded_integrator: Optional[EmbeddedRungeKuttaMethod] = None

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(
            simulation_kernel=simulation_kernel,
            init_stage=init_stage,
        )
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            self._integration_method = pg.Integration[
                self.integration_method]
            if self._integration_method in {
                pg.Integration.RUNGE_KUTTA_FEHLBERG,
                pg.Integration.RUNGE_KUTTA_FEHLBERG_4,
                pg.Integration.RUNGE_KUTTA_FEHLBERG_45,
            }:
                self._embedded_integrator = RKFehlberg45()

    def get_integration_method(self) -> 'pg.Integration':
        return self._integration_method

    @property
    def embedded_integrator(self) -> Optional[EmbeddedRungeKuttaMethod]:
        return self._embedded_integrator

    def predict(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule',
            sim_time: float,
            delta_time: float,
            update_molecule: bool = True,
    ) -> Tuple['pg.Molecule', np.ndarray, float]:
        object_id = molecule.object_id
        position_global = molecule.position
        new_pos_global = molecule.position
        scene_manager = simulation_kernel.get_scene_manager()
        # Estimation error; will stay 0 for incompatible integration types:
        error = 0

        # FIXME: Molecule might has no attached object
        if object_id is not None:
            if self._integration_method in {
                    pg.Integration.EULER, pg.Integration.RUNGE_KUTTA_4}:
                flow = scene_manager.get_flow_by_position(
                    simulation_kernel,
                    position_global,
                    object_id,
                    sim_time
                )
                k1 = delta_time * flow
                if self._integration_method == pg.Integration.EULER:
                    new_pos_global = position_global + k1
                elif self._integration_method == pg.Integration.RUNGE_KUTTA_4:
                    # TODO(jdrees): Take the time difference between k1
                    #  and k2-k4 into account.
                    k2 = delta_time * scene_manager.get_flow_by_position(
                        simulation_kernel,
                        position_global + (k1 / 2),
                        object_id,
                        sim_time
                    )
                    k3 = delta_time * scene_manager.get_flow_by_position(
                        simulation_kernel,
                        position_global + (k2 / 2),
                        object_id,
                        sim_time
                    )
                    k4 = delta_time * scene_manager.get_flow_by_position(
                        simulation_kernel,
                        position_global + k3,
                        object_id,
                        sim_time
                    )
                    new_pos_global = (
                        position_global
                        + (1 / 6 * k1)
                        + (1 / 3 * k2)
                        + (1 / 3 * k3)
                        + (1 / 6 * k4)
                    )
                else:
                    raise AssertionError(
                        "This should really never ever happen."
                    )
            elif self._integration_method in {
                    pg.Integration.RUNGE_KUTTA_FEHLBERG,
                    pg.Integration.RUNGE_KUTTA_FEHLBERG_4,
                    pg.Integration.RUNGE_KUTTA_FEHLBERG_45,
            }:
                (
                    new_pos_global,
                    new_pos_low_global,
                    pos_err
                ) = self._embedded_integrator.compute(
                    func=lambda t, y: scene_manager.get_flow_by_position(
                        simulation_kernel=simulation_kernel,
                        position_global=y,
                        object_id=object_id,
                        sim_time=t,
                    ),
                    t_old=sim_time,
                    y_old=position_global,
                    dt=delta_time
                )
                error = np.linalg.norm(pos_err)
                if self._integration_method \
                        == pg.Integration.RUNGE_KUTTA_FEHLBERG_4:
                    new_pos_global = new_pos_low_global
            else:
                raise NotImplementedError(
                    "Integration type is not implemented yet"
                )

        # FIXME: Primitive implementation of displacement by velocity
        # after(!) displacement due to vector field
        new_pos_global += molecule.velocity * delta_time

        if update_molecule:
            molecule.update(
                scene_manager=scene_manager,
                new_pos_global=new_pos_global,
            )
        return molecule, new_pos_global, error
