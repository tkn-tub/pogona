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

import logging

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class PlotterTerminal(pg.Component):
    """
    Produces additional logging output in each time step.
    """

    log_all_molecules = prop.BoolProperty(False, required=False)
    log_first_molecule = prop.BoolProperty(False, required=False)

    def __init__(self):
        super().__init__()

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        # Nothing else to do here in this class.

    # noinspection PyMethodMayBeStatic
    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        sk = simulation_kernel
        LOG.info(f"--- Time Step {round(sk.get_simulation_time(), 10)} ---")
        LOG.info(
            "Current number of molecules: "
            f"{len(sk.get_molecule_manager().get_all_molecules())}"
        )
        if (
                self.log_first_molecule
                and len(sk.get_molecule_manager().get_all_molecules()) > 0
        ):
            LOG.info(
                sk.get_molecule_manager().get_all_molecules().values()[0]
                # ^ TODO: sorted() by keys?
            )
        if self.log_all_molecules:
            for molecule in \
                    sk.get_molecule_manager().get_all_molecules().values():
                LOG.debug(molecule)
                break
