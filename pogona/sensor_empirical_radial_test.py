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

import os
import csv
import numpy as np
import scipy.stats
import logging
from typing import Tuple

import pogona as pg
import pogona.properties as prop

LOG = logging.getLogger(__name__)


class SensorEmpiricalRadialTest(pg.Sensor):
    """
    Sensor based on empirical measurements in a magnetic field simulation.
    The model used in this class doesn't actually fit the data all that well.
    This class should only be used for testing how much of a difference
    such a model will make if it also considers susceptibility differences
    in the radial direction.

    For this, we shall assume that molecules pass through the
    sensor in positive (object-local!) z direction and that the sensor
    (i.e., the boundary) is 25 mm long!
    So remember to rotate this sensor via the transformation accordingly
    if your particles aren't moving from -z to +z.
    """

    POPT = [5.87697665e-01, 1.53675354e+00, -6.59646889e-01, 8.91311070e-03,
            1.63605094e+01, 1.35037185e-03, 7.07910938e+00, 3.87609999e+01,
            3.27091249e-01, 2.63243226e+00, 2.18561674e+00, 2.43038985e-03,
            6.23107849e-03]
    """Parameters for model_flux determined by curve fitting."""

    log_folder = prop.StrProperty("", required=False)
    """The file `sensor[<component name>].csv` will be created in here."""

    def __init__(self):
        super().__init__()

        self._relative_susceptibility: float = 0
        """
        Sum of all particle susceptibilities currently within the sensor.
        Susceptibility is relative to the maximum susceptibility measured
        in the variability experiment mentioned above.
        """
        self._csv_file = None
        self._csv_writer = None

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(simulation_kernel, init_stage)
        if init_stage == pg.InitStages.CREATE_FOLDERS:
            os.makedirs(
                os.path.join(
                    simulation_kernel.results_dir,
                    self.log_folder),
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
                    f'sensor[{name}].csv'
                ),
                mode='w'
            )
            fieldnames = ['sim_time', 'rel_susceptibility']
            self._csv_writer = csv.writer(
                self._csv_file,
                delimiter=',',
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )
            self._csv_writer.writerow(fieldnames)

    def finalize(self, simulation_kernel: 'pg.SimulationKernel'):
        self._csv_file.close()

    @staticmethod
    def model_flux(
        ax_rad: Tuple[np.ndarray, np.ndarray],
        a1, a2, a3, a4, a5,
        b1, b2, b3, b4, b5, b6,
        c1, c2
    ):
        """
        Polynomial of degree 4 (in radial direction)
        where every relevant parameter is
        logistically distributed (in axial direction)…

        The idea is that in a*x^4, a should be able
        to change from positive to negative and back to positive
        with changing axial positions.
        """
        axial, radial = ax_rad
        return (
            # degree 4:
            (
                    scipy.stats.genlogistic.pdf(axial, 1, loc=0, scale=a1)
                    * a2
                    + a3
            )
            * ((scipy.stats.genlogistic.pdf(axial, 1, loc=0,
                                            scale=a4) * a5) * radial) ** 4
            # degree 2:
            + (
                    scipy.stats.genlogistic.pdf(axial, 1, loc=0, scale=b1)
                    * b2
                    + b3
            )
            * ((scipy.stats.genlogistic.pdf(axial, 1, loc=0,
                                            scale=b4) * b5 + b6) * radial) ** 2
            # degree 0:
            + scipy.stats.genlogistic.pdf(axial, 1, loc=0, scale=c1) * c2
        )

    def process_molecule_moving(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        pos_local = self._transformation.apply_inverse_to_point(
                molecule.position)
        if not self.is_inside_sensor_zone(position_global=molecule.position):
            return
        # Local coordinates are in the interval [0, 1] and should be scaled.
        axial = pos_local[2] * self._transformation.scaling[2]
        radial = np.sqrt(
            np.square(pos_local[0] * self._transformation.scaling[0])
            + np.square(pos_local[1] * self._transformation.scaling[1])
        )
        LOG.debug(
            f"{pos_local * self._transformation.scaling},"
            f" radial pos = {radial:.3f},"
            f" axial pos = {axial:.3f}"
        )
        self._relative_susceptibility += self.model_flux(
            (
                # Axial position:
                axial,
                # Radial position:
                radial
            ),  # TODO: ax_rad tuple!
            *SensorEmpiricalRadialTest.POPT
        )

    def process_new_time_step_after(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        LOG.info(
            f"Sensor {self.sensor_id}: {self._relative_susceptibility:3e} "
            "susceptibility"
        )
        self._csv_writer.writerow([
            simulation_kernel.get_simulation_time(),
            self._relative_susceptibility
        ])
        self._relative_susceptibility = 0
