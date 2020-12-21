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
import enum
import logging
import scipy.stats

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class KnownSensors(enum.Enum):
    NONE = 1
    MS2G_BARTINGTON = 2
    ERLANGEN_20200310 = 3


class SensorEmpirical(pg.Sensor):
    """
    Sensor based on empirical measurements of susceptibility
    variations within a susceptometer.

    For this, we shall assume that molecules pass through the
    sensor in positive (object-local!) z direction and that the sensor
    (i.e., the boundary) is 25 mm long!
    So remember to rotate this sensor via the transformation accordingly
    if your particles aren't moving from -z to +z.
    """

    DEFAULT_FCT_PARAMS = {
        KnownSensors.MS2G_BARTINGTON: [  # scale sensor to 25 mm
            1.1710899115768234,
            0.012806480117364473,
            0.0017908368596852163
        ],
        KnownSensors.ERLANGEN_20200310: [  # scale sensor to 35 mm
            1.1521874852663174, 0.017531424609419782, 0.003804701283874202
        ],
    }
    """
    Default distribution parameters for known sensors.
    Values determined using curve fitting for the logistic function.
    """

    log_folder = prop.StrProperty("sensor_data", required=False)
    """The file `sensor[<component name>].csv` will be created in here."""

    use_known_sensor = prop.EnumProperty(
        str(KnownSensors.MS2G_BARTINGTON.name),
        name='use_known_sensor',
        required=False,
        enum_class=KnownSensors,
    )
    """
    Use distribution parameters obtained for known sensors in previous
    experiments.

    Default: MS2G_BARTINGTON
    """
    distribution_params = prop.FloatArrayProperty(
        default=DEFAULT_FCT_PARAMS[KnownSensors.MS2G_BARTINGTON],
        required=False,
    )
    """
    Distribution parameters obtained from curve fitting,
    for now applied to a logistic function by default.
    Alternatively, use `use_known_sensor`.
    """

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
        elif init_stage == pg.InitStages.CHECK_ARGUMENTS:
            if self.use_known_sensor != KnownSensors.NONE.name:
                self.distribution_params = self.DEFAULT_FCT_PARAMS[
                    KnownSensors[self.use_known_sensor]
                ]

    def finalize(self, simulation_kernel: 'pg.SimulationKernel'):
        self._csv_file.close()

    def process_molecule_moving_after(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            molecule: 'pg.Molecule'
    ):
        pos_local = self._transformation.apply_inverse_to_point(
                molecule.position)
        if not self.is_inside_sensor_zone(position_global=molecule.position):
            return
        # Local coordinates are in the interval [0, 1] and should be scaled.
        self._relative_susceptibility += scipy.stats.genlogistic.pdf(
            (
                (pos_local[2] + 0.5)  # Geometry is centered around origin
                * self._transformation.scaling[2]
            ),
            *self.distribution_params
        )

    def process_new_time_step(
        self,
        simulation_kernel: 'pg.SimulationKernel',
        notification_stage: 'pg.NotificationStages',
    ):
        if notification_stage != pg.NotificationStages.LOGGING:
            return
        LOG.info(
            f"\"{self.component_name}\": "
            f"{self._relative_susceptibility:.3e} susceptibility"
        )
        self._csv_writer.writerow([
            simulation_kernel.get_simulation_time(),
            self._relative_susceptibility
        ])
        self._relative_susceptibility = 0
