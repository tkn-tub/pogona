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
from typing import Optional, Callable

LOG = logging.getLogger(__name__)


class ModulationPPM(pg.ModulationOOK):
    """
    Separates the symbol duration into N chips for N-PPM.

    """

    chips_per_symbol = prop.IntProperty(2, required=False)
    """Must be a power of 2 and greater than 1."""

    def __init__(self):
        super().__init__()

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if (
                    self.chips_per_symbol < 2 or
                    not pg.util.is_power_of_two(self.chips_per_symbol)
            ):
                raise ValueError(
                    f"{self.chips_per_symbol=}, but must be a power of "
                    "2 and greater than 1."
                )

    @property
    def chip_duration(self) -> float:
        try:
            return self.injection_duration + self.pause_duration
        except TypeError:
            # TODO: this failed once b/c pause_duration couldn't be cast to
            #  float -> improve property checking!
            raise TypeError(
                f"Sum didn't work, {self.injection_duration=}, "
                f"{self.pause_duration=}, type inj dur "
                f"{type(self.injection_duration)}, "
                f"type pause dur {type(self.pause_duration)}"
            )

    @property
    def symbol_duration(self) -> float:
        # The actual symbol duration is chip_duration * chips_per_symbol,
        # but this property is used in Modulation.transmit_bitstream,
        # among other places, expecting the duration of one injection plus
        # pause.
        return self.chip_duration

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        super().process_new_time_step(simulation_kernel, notification_stage)

    @staticmethod
    def bitstream_to_ppm(bitstream: str, chips_per_symbol: int) -> str:
        """
        Convert bitstream into PPM bitstream,
        e.g., 101101 for 2-PPM: 01|10|01|01|10|01
        or 101101 for 4-PPM: 0010|0001|0100
        or 101101 for 8-PPM: 000001000|00000100
        """
        assert pg.util.is_power_of_two(chips_per_symbol)
        bits_per_symbol = chips_per_symbol.bit_length() - 1  # == log2(chips)
        result = ""
        for bits_tuple in pg.util.grouper(
                bitstream, n=bits_per_symbol, fillvalue='0'):
            symbol_int = int(''.join(bits_tuple), base=2)
            result += (
                symbol_int * '0'
                + '1'
                + (chips_per_symbol - symbol_int - 1) * '0'
            )
        return result

    def transmit_bitstream(
            self,
            bitstream: str,
            simulation_kernel: 'pg.SimulationKernel',
            finish_callback: Optional[Callable]
    ):
        super().transmit_bitstream(
            bitstream=bitstream,
            simulation_kernel=simulation_kernel,
            finish_callback=finish_callback,
        )
        self._bitstream = self.bitstream_to_ppm(
            bitstream=bitstream,
            chips_per_symbol=self.chips_per_symbol,
        )
        self._bitstream_duration = self.chip_duration * len(self._bitstream)
        LOG.warning(
            f"Transmitting bitstream\n{bitstream}\nconverted to\n"
            f"{self._bitstream}\n"
            f"{self._bitstream_duration=} for {self.chips_per_symbol=} and "
            f"{self.pause_duration=} and {self.chip_duration=}"
        )
