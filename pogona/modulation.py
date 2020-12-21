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
import numpy as np
import logging
from typing import Optional, Callable
from abc import ABCMeta, abstractmethod

LOG = logging.getLogger(__name__)


class Modulation(pg.Component, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self._calling_bitstream_generator: Optional[
            'pg.BitstreamGenerator'] = None
        self._is_transmitting = False
        """
        Whether or not a bitstream is currently being transmitted
        """
        self._start_time: float = np.inf
        """
        Simulation time in seconds at which we started transmitting the current
        bitstream.
        Initially set to infinity so that nothing will be transmitted
        before the first call to transmit_bitstream().
        """
        self._bitstream: str = ""
        """
        Currently transmitting bit stream
        """
        self._bitstream_duration: float = 0
        """
        Duration of the currently transmitting bit stream in seconds
        """
        self._finish_callback: Optional[Callable] = None
        """
        Function that should get called upon transmission finish
        """

    @property
    @abstractmethod
    def symbol_duration(self):
        pass

    def transmit_bitstream(
            self,
            bitstream: str,
            simulation_kernel: 'pg.SimulationKernel',
            finish_callback: Optional[Callable]):
        if self._is_transmitting:
            raise AssertionError("Trying to transmit two bitstreams at once")
        self._is_transmitting = True
        self._start_time = simulation_kernel.get_simulation_time()
        self._bitstream = bitstream
        self._finish_callback = lambda: finish_callback(simulation_kernel)
        self._bitstream_duration = self.symbol_duration * len(bitstream)

    def _finish_transmission(self):
        self._is_transmitting = False
        if self._finish_callback is not None:
            self._finish_callback()
