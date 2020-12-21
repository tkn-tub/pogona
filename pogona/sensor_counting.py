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

import os.path
import csv
import logging

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SensorCounting(pg.Sensor):
    log_folder = prop.StrProperty("sensor_data", required=False)
    """The file `sensor[<component name>].csv` will be created in here."""

    def __init__(self):
        super().__init__()

        self._counts = 0
        """Number of molecules in this sensor so far in this time step."""
        self._csv_writer = None
        self._csv_file = None

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CREATE_FOLDERS:
            os.makedirs(
                os.path.join(simulation_kernel.results_dir, self.log_folder),
                exist_ok=True
            )
        elif init_stage == pg.InitStages.CREATE_FILES:
            name = (
                self.id
                if self.component_name == "Generic component"
                else self.component_name
            )
            self._csv_file = open(
                os.path.join(
                    simulation_kernel.results_dir,
                    self.log_folder,
                    f"sensor[{name}].csv"
                ),
                mode='w'
            )
            fieldnames = ['sim_time', 'molecule_count']
            self._csv_writer = csv.writer(
                self._csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )
            self._csv_writer.writerow(fieldnames)

    def finalize(self, simulation_kernel: 'pg.SimulationKernel'):
        self._csv_file.close()

    def process_molecule_moving_after(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        if self.is_inside_sensor_zone(position_global=molecule.position):
            self._counts = self._counts + 1

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        LOG.debug(f"Sensor {self.id}: {self._counts} molecules in zone.")
        # TODO(jdrees): Is the sim_time off by one time step?
        #               Investigate and refactor if necessary
        self._csv_writer.writerow([
            simulation_kernel.get_simulation_time(),
            self._counts
        ])
        self._counts = 0
