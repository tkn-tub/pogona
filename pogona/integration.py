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

from enum import Enum


class Integration(Enum):
    EULER = 1
    RUNGE_KUTTA_4 = 2
    RUNGE_KUTTA_FEHLBERG = 3
    """
    An embedded Runge-Kutta method; allows for adaptive time stepping.
    Equivalent to RUNKE_KUTTA_FEHLBERG_45.
    """
    RUNGE_KUTTA_FEHLBERG_4 = 4
    """
    For testing purposes: Uses RUNGE_KUTTA_FEHLBERG for computation,
    but uses only the lower-order result for movement prediction.
    """
    RUNGE_KUTTA_FEHLBERG_45 = 5
    """
    An embedded Runge-Kutta method; allows for adaptive time stepping.
    Compares 4-th order with 5-th order to get an error measure.
    """

    @staticmethod
    def supports_time_step_control(integration: 'Integration'):
        """
        :param integration:
        :return: True iff the given integration supports adaptive
            time step control.
        """
        return integration in {
            Integration.RUNGE_KUTTA_FEHLBERG,
        }
