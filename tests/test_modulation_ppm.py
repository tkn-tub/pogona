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


def test_bitstream_to_ppm():
    bs = '101101'
    assert (
            pg.ModulationPPM.bitstream_to_ppm(bitstream=bs, chips_per_symbol=2)
            == '011001011001'
    )
    assert (
            pg.ModulationPPM.bitstream_to_ppm(bitstream=bs, chips_per_symbol=4)
            == '001000010100'
    )
    assert (
            pg.ModulationPPM.bitstream_to_ppm(bitstream=bs, chips_per_symbol=8)
            == '0000010000000100'
    )

    bs = '010010110101'
    assert(
        pg.ModulationPPM.bitstream_to_ppm(bitstream=bs, chips_per_symbol=4)
        == '010010000010000101000100'
    )
