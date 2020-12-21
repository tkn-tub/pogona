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
import numpy as np
import logging
from typing import Optional

LOG = logging.getLogger(__name__)


class ModulationOOK(pg.Modulation):
    injection_volume = prop.FloatProperty(0, required=False)
    """
    Injection volume for each bit in litres.
    If this is given, `injection_duration` should be 0 as it will
    be determined by the pump model.
    In this case, `pause_duration` will be equal to the cycle duration
    and independent of how long an injection takes.
    Take care to not let injections overlap.
    """
    injection_duration = prop.FloatProperty(0, required=False)
    """
    Duration of one injection in seconds.
    If a bit stream is given, the injection_duration specifies the
    duration of the injection for each individual bit.
    """
    pause_duration = prop.FloatProperty(0, required=False)
    """
    Time in seconds to wait *after*
    an injection (with `injection_duration`)
    before injecting the next pulse
    or, if `ascii_sequence` or `bit_sequence` is given,
    the time to wait before injecting the next bit.
    """
    attached_injector = prop.ComponentReferenceProperty(
        '',
        required=True,
        can_be_empty=False,
    )
    """Component name of the attached injector."""
    attached_destructor = prop.ComponentReferenceProperty(
        '',
        required=False,
        can_be_empty=True,
    )
    """
    Component name of the attached destructor.
    """
    attached_pump = prop.ComponentReferenceProperty(
        '',
        required=True,
        can_be_empty=False,
    )
    """
    Component name of the attached pump.
    A pump is required for coordinating the timing of an injection.
    Consider using an ObjectPumpTimed if you are not dealing with injection
    volumes or fluid vector fields in general.
    """

    use_burst = prop.BoolProperty(False, required=False)
    """
    By default, the attached injector is turned on
    in every time step. If use_burst is True, however,
    it will only be turned on at the beginning of an injection.
    """

    def __init__(self):
        super().__init__()
        self._attached_injector: Optional['pg.Injector'] = None
        self._attached_destructor: Optional['pg.SensorDestructing'] = None
        self._attached_pump: Optional['pg.objects.ObjectPumpVolume'] = None
        self._is_injecting = False
        self._most_recent_pulse_number = -1

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            # Half-mandatory arguments:
            if (self.attached_injector not in
                    simulation_kernel.get_components()):
                raise ValueError(
                    "No injector component with the name "
                    f"{self.attached_injector} attached to the simulation "
                    f"kernel could be found."
                )
            if self.attached_pump not in simulation_kernel.get_components():
                raise ValueError(
                    "No pump component with the name "
                    f"\"{self.attached_pump}\" attached to the simulation "
                    "kernel could be found.\n"
                    "Available components are: "
                    + ", ".join(simulation_kernel.get_components())
                )
            if (self.attached_destructor != ""
                    and self.attached_destructor not in
                    simulation_kernel.get_components()):
                raise ValueError(
                    "No destructor component with the name "
                    f"\"{self.attached_destructor}\" attached to the "
                    f"simulation kernel could be found."
                )
        elif init_stage == pg.InitStages.BUILD_SCENE:
            if (self.attached_destructor is not None
                    and self.attached_destructor != ""):
                self._attached_destructor = simulation_kernel.get_components()[
                    self.attached_destructor
                ]
            self._attached_injector = simulation_kernel.get_components()[
                self.attached_injector
            ]
            self._attached_pump = simulation_kernel.get_components()[
                self.attached_pump
            ]

    @property
    def symbol_duration(self):
        return self.injection_duration + self.pause_duration

    def _start_injection(
            self,
            simulation_kernel: 'pg.SimulationKernel',
    ):
        self._attached_pump.start_injection(
            simulation_kernel=simulation_kernel,
        )

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.MODULATION:
            return
        if (self._start_time == np.inf
                or simulation_kernel.get_simulation_time()
                > self._start_time + self._bitstream_duration):
            # We have finished transmitting the stream, nothing to do
            return
        pulse_number = int(np.floor(
            (simulation_kernel.get_simulation_time() - self._start_time)
            / self.symbol_duration
        ))
        """
        0-based index of the pulse for the current sim_time.
        If `self.bit_sequence` is set, this include pulses for which the
        sequence has a value of 0.
        """

        pulse_beginning = (
            self._start_time + pulse_number * self.symbol_duration
        )

        if (
                pulse_number >= len(self._bitstream)
                or self._bitstream[pulse_number] == '0'
        ):
            return

        if (pulse_beginning <= simulation_kernel.get_simulation_time()
                # Prevent restarting during an injection:
                and not self._is_injecting
                # Prevent restarting after an injection has ended:
                and pulse_number > self._most_recent_pulse_number):
            # Then start a new injection:
            self._is_injecting = True
            self._most_recent_pulse_number = pulse_number
            if not self.use_burst:
                # TODO: write pytest w/ and w/o burst
                self._attached_injector.turn_on()
            else:
                self._attached_injector.inject_burst()
                if self._attached_destructor is not None:
                    self._attached_destructor.turn_off()

            self._start_injection(
                simulation_kernel=simulation_kernel,
            )

        # Check if this is the last time step of an injection (!= cycle):
        if self._is_injecting and not self._attached_pump.is_active:
            self._is_injecting = False
            if not self.use_burst:
                self._attached_injector.turn_off()
            else:
                if self._attached_destructor is not None:
                    self._attached_destructor.turn_on()

        # self._attached_pump will process this time step after all
        # Modulation instances have done the same.
