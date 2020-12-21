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

import csv
import os
import logging

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class PlotterCSV(pg.Component):
    """Writes molecule positions to CSVs."""

    write_interval = prop.IntProperty(1, required=False)
    """
    Allows skipping time steps if other than 1.
    For example, `writer_interval=3` will produce a CSV file in
    time step 0, then do nothing in time steps 1 and 2, then
    write again in time step 3.
    """
    folder = prop.StrProperty("", required=False)
    """
    Output folder for molecule positions relative to results_dir of the kernel.
    A series of CSV files will be created here, one for each time step.
    """

    def __init__(self):
        super().__init__()

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CREATE_FOLDERS:
            path = os.path.join(
                simulation_kernel.results_dir,
                self.folder
            )
            os.makedirs(path, exist_ok=True)

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        sk = simulation_kernel
        if sk.get_elapsed_base_time_steps() % self.write_interval != 0:
            return

        with open(
                os.path.join(
                    simulation_kernel.results_dir,
                    self.folder,
                    "positions.csv." + str(sk.get_elapsed_base_time_steps())
                ),
                mode='w'
        ) as csv_file:
            fieldnames = ['id', 'x', 'y', 'z', 'cell_id', 'object_id']
            writer = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )

            writer.writerow(fieldnames)
            for molecule in \
                    sk.get_molecule_manager().get_all_molecules().values():
                writer.writerow((
                    molecule.id,
                    molecule.position[0],
                    molecule.position[1],
                    molecule.position[2],
                    molecule.cell_id,
                    molecule.object_id
                ))
