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
from typing import Optional

LOG = logging.getLogger(__name__)


class BitstreamGenerator(pg.Component):
    start_time = prop.FloatProperty(0, required=False)
    """
    At what simulated time in seconds to start the sequence transmission.
    """
    repetitions = prop.IntProperty(1, required=False)
    """
    Number of times the sequence is to be repeated.
    """
    bit_sequence = prop.StrProperty("1", required=False)
    """
    Which bit sequence to transmit.
    A valid input would be "101010", for example.
    Synchronization bits will not be inserted automatically!

    Will be overridden if `ascii_sequence` is set.
    """
    ascii_sequence = prop.StrProperty('', required=False)
    """
    If given, overrides bit_sequence with a bit
    sequence generated from the ASCII characters.
    A valid input would be b"HELLO_WORLD", for example.

    Overrides `self.bit_sequence.`
    """
    attached_modulation = prop.StrProperty("", required=False)

    def __init__(self):
        super().__init__()
        self._attached_modulation: Optional['pg.Modulation'] = None
        self._current_repetition = 0
        """
        Which iteration of the resending (self.repetitions) we are in
        """

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if (self.attached_modulation not in
                    simulation_kernel.get_components()):
                raise ValueError(
                    "No modulation component with the name "
                    f"{self.attached_modulation} attached to the simulation "
                    "kernel could be found."
                )
        elif init_stage == pg.InitStages.BUILD_SCENE:
            self._attached_modulation = simulation_kernel.get_components()[
                self.attached_modulation]

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.BITSTREAMING:
            # TODO: Find a more appropriate name for this stage…
            #  Should still happen before MODULATION though, for consistency.
            return
        if simulation_kernel.get_simulation_time() > self.start_time \
                and self._current_repetition == 0:
            self._start_stream_transmission(simulation_kernel)

    def set_arguments(self, **kwargs):
        super().set_arguments(**kwargs)

        # Convert the ascii sequence to a bit sequence.
        # Doing this here rather than in initialize (stage CHECK_ARGUMENTS)
        # so that the resulting bit sequence can be checked from outside
        # before the kernel starts.

        if self.ascii_sequence is not None and self.ascii_sequence != '':
            for char in self.ascii_sequence.encode():
                if char < 64 or char > 95:
                    raise ValueError(
                        "ascii_sequence does not support ASCII characters "
                        "below the decimal value of 64 or above 95, "
                        "because with the current decoding scheme "
                        "(as hinted to in unterweger2018experimental, "
                        "DOI 10.1109/SPAWC.2018.8446011, section II D), "
                        "we rely on the '010' prefix for synchronization. "
                        f"The character '{chr(char)}'={char} "
                        f"is therefore invalid."
                    )
            self.bit_sequence = ''.join([
                # Convert to binary, zero-pad to full bytes:
                f"{char:08b}" for char in self.ascii_sequence.encode()
            ])
            LOG.info(
                f"Converted ASCII sequence '{self.ascii_sequence}' to "
                f"bit sequence '{self.bit_sequence}'."
            )

    def _start_stream_transmission(self, simulation_kernel):
        # Initialize a transmission by handing it to the modulation
        self._current_repetition += 1
        self._attached_modulation.transmit_bitstream(
            self.bit_sequence,
            simulation_kernel,
            finish_callback=self.finished_stream_transmission,
        )

    def finished_stream_transmission(
            self,
            simulation_kernel: 'pg.SimulationKernel'
    ):
        # Callback from the modulation that the last stream was transmitted
        if self._current_repetition < self.repetitions:
            # We still need to transmit the sequence another time
            self._start_stream_transmission(
                simulation_kernel=simulation_kernel
            )
