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


class Interpolation(Enum):
    NEAREST_NEIGHBOR = 1
    SHEPARD = 2
    MODIFIED_SHEPARD = 3
    MODIFIED_SHEPARD_LINEAR = 4
    MODIFIED_SHEPARD_SQUARED = 5
    MODIFIED_SHEPARD_CUBED = 6
    MODIFIED_SHEPARD_FOURTH = 7
    NONE = 8
