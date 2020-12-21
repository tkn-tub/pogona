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
from .object_pump_volume import ObjectPumpVolume


class ObjectPumpPeristaltic(ObjectPumpVolume):
    r"""
    Model for a peristaltic pump that tries to avoid overdosing by
    ramping down the flow speed towards the end of an injection.

    We want the injection volume to remain constant.
    For a static flow pump (ObjectPumpVolume), the flow rate :math:`r` is
    constant over the entire injection duration :math:`T` and equal to
    the maximum flow rate :math:`R`.

    At the end of what would be a constant injection, we stop at time
    :math:`T-t` and decrease the flow speed linearly in :math:`n` steps.
    In order to maintain the original injection volume, the following
    must hold for intermediate flow rates :math:`h_i`:

    .. math::
        \sum_{i=0}^{n-1} h_i \cdot s &= t \cdot R \\
        \Rightarrow h_i &= \frac{n-i}{n+1} \cdot R

    The step size :math:`s` must thus be

    .. math::
        s &= t \cdot R \cdot \left(\sum_{i=0}^{n-1} h_i\right)^{-1} \\
          &= tR\left(\frac{Rn}{2}\right)^{-1} = \frac{2t}{n}.

    If we don't want to define the time :math:`t` we want to cut off
    from the original injection duration, but instead the ramp-down time
    :math:`t_s`, we can convert between it and :math:`t` like so:

    .. math::
        t_s = n \cdot s = 2t
    """
    # TODO: brand and model number of the pump

    name = prop.StrProperty("Peristaltic pump", required=False)

    ramp_down_steps = prop.IntProperty(1, required=False)
    """
    Number of in-between steps between the highest flow rate and
    the pump being turned off.
    """

    ramp_down_time = prop.FloatProperty(0, required=False)
    """
    A constant time in which to linearly ramp down the flow speed
    from its maximum to 0.

    Should be lower than twice of what the injection duration would
    be if the flow rate were constant.
    If equal to twice this hypothetical injection duration,
    the injection should start with the first intermediate step
    immediately.

    In the limited data we have so far (for lack of a proper
    high-speed camera), it looks as though this time is constant
    for a given flow rate and varying injection volumes.
    """

    def __init__(self):
        super().__init__()

        self._static_flow_injection_duration = 0
        self._most_recent_ramp_index = -1
        self._target_injection_flow_mlpmin = 0

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            pass

    def start_injection(
            self,
            simulation_kernel: 'pg.SimulationKernel',
    ):
        """
        Start an injection.

        Warning: ObjectPumpPeristaltic only supports injection_volume,
            not injection_duration.
        """
        self._target_injection_flow_mlpmin = self.injection_flow_mlpmin
        self._static_flow_injection_duration = (
            self.injection_volume_l
            / pg.util.mlpmin_to_lps(self.injection_flow_mlpmin)
        )
        self._t_end_injection = (
            simulation_kernel.get_simulation_time()
            + self._static_flow_injection_duration
            + self.ramp_down_time / 2
        )
        self._set_current_pump_flow(
            simulation_kernel=simulation_kernel,
            flow_rate=self.injection_flow_mlpmin,
        )
        self._is_active = True

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        # Ensure this method is always called after a Modulation instance
        # has made its changes in this time step:
        if notification_stage != pg.NotificationStages.PUMPING:
            return
        if not self._is_active:
            return
        t_sim = simulation_kernel.get_simulation_time()
        t_start_ramping = self._t_end_injection - self.ramp_down_time
        if t_sim < t_start_ramping:
            return
        if t_sim >= self._t_end_injection:
            self._is_active = False
            self._most_recent_ramp_index = -1
            self._set_current_pump_flow(
                simulation_kernel=simulation_kernel,
                flow_rate=0,
            )
            return
        ramp_down_step_index = int(
            (t_sim - t_start_ramping) / self.ramp_down_time
            * float(self.ramp_down_steps)
        )
        if ramp_down_step_index <= self._most_recent_ramp_index:
            return  # should never be '<' though
        # Proceed with the next ramp-down step:
        self._most_recent_ramp_index = ramp_down_step_index
        self._set_current_pump_flow(
            simulation_kernel=simulation_kernel,
            flow_rate=(
                self._target_injection_flow_mlpmin
                * (self.ramp_down_steps - ramp_down_step_index)
                / (self.ramp_down_steps + 1)
            )
            # TODO: make sure vector fields can be found for all
            #  intermediate steps
        )
