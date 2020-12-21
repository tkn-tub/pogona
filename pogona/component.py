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

from abc import ABC
from typing import Set, cast
from enum import Enum
import logging
import inspect

import pogona as pg
import pogona.properties as prop


LOG = logging.getLogger(__name__)


class InitStages(Enum):
    """
    Initialization stages for ensuring that :class:`~pogona.Component`
    instances are initialized in the right order.

    InitStages are executed in increasing order of their respective
    value (i.e., in the order as listed in the source file,
    not as listed in the documentation).
    """

    CHECK_ARGUMENTS = 1
    """Check validity of arguments."""
    BUILD_SCENE = 2
    CREATE_FOLDERS = 3
    CREATE_FILES = 4
    CREATE_DATA_STRUCTURES = 5
    CREATE_TELEPORTERS = 6
    REGISTER_SENSORS = 7
    CREATE_SENSOR_SUBSCRIPTIONS = 8
    SET_UP_FLOW_SYSTEM = 9
    START_SIMULATION = 10


class NotificationStages(Enum):
    BITSTREAMING = 1  # TODO: find a more appropriate name
    MODULATION = 2
    DESTRUCTING = 3
    SPAWNING = 4
    PUMPING = 5
    LOGGING = 7


class Component(ABC):
    """
    Base class for simulation components that can be configured via
    YAML files.
    """

    component_name = prop.StrProperty(
        default="Generic component",
        required=False,
    )
    """
    Unique name of this component, unless it is "Generic component".
    """

    def __init__(self):
        self.id = -1
        """Unique integer component ID"""

        self._arguments_already_set: Set[str] = set()
        """
        Names of arguments already set via `set_arguments()`
        Mandatory arguments not in this set at the time when `initialize()`
        is first called will cause an exception.
        """
        self._mandatory_arguments: Set[str] = set()
        """
        Names of arguments that should cause an exception if they are not set
        by the time `initialize()` is first called.
        """
        self._ignored_arguments: Set[str] = set()
        """
        Names of arguments that should not trigger an exception if they are
        passed via set_arguments.
        """

        # Convert class properties to instance variables, using their default
        # values. Any value can be overwritten with `set_arguments()`.
        # Having properties at the class level lets us read type annotations
        # and docstrings for the UI in the Blender add-on.
        properties = dict()
        for attr_name, class_attr in inspect.getmembers(
                self.__class__,
                lambda m: isinstance(m, prop.AbstractProperty)
        ):
            if not isinstance(class_attr, prop.AbstractProperty):
                continue
            current_prop = cast(prop.AbstractProperty, class_attr)
            properties[attr_name] = current_prop
            if current_prop.required:
                self._mandatory_arguments.add(attr_name)
        self._property_names = set(properties.keys())
        self.__dict__.update(properties)

    def set_arguments(self, **kwargs):
        """
        Read arguments as key value pairs and set this component's
        member variables accordingly.
        Validity of the argument values will be checked in
        :meth:`~pogona.Component.initialize`.
        """
        unrecognized_args = (
            set(kwargs.keys())
            - self._property_names
            - self._ignored_arguments
        )
        if len(unrecognized_args) != 0:
            # LOG.warning(
            raise TypeError(
                "Unrecognized arguments for component of type "
                f"{self.__class__}: "
                + ", ".join(unrecognized_args)
                + " -- Valid arguments: "
                + ", ".join(self._property_names - self._ignored_arguments)
            )
        self.__dict__.update(kwargs)
        for key in kwargs.keys():
            self._arguments_already_set.add(key)

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        """
        Use :class:`~pogona.InitStages` to initialize this Component
        instance.
        """
        if init_stage == InitStages.CHECK_ARGUMENTS:
            missing_args = (
                self._mandatory_arguments - self._arguments_already_set
            )
            if len(missing_args) != 0:
                raise TypeError(
                    "Missing mandatory arguments for component "
                    f"\"{self.component_name}\" with ID {self.id} "
                    f"of class {self.__class__}: "
                    + ", ".join(list(missing_args))
                )

            # Iterate over all AbstractProperties of the current class
            # for additional safety checks.
            # (Not iterating over items of this instance as they may have
            # been overwritten with configuration values, replacing
            # the AbstractProperty instances.)
            for attr_name, class_attr in inspect.getmembers(
                    self.__class__,
                    lambda m: isinstance(m, prop.AbstractProperty)
            ):
                instance_attr = getattr(self, attr_name)
                if isinstance(class_attr, prop.EnumProperty):
                    # Make sure that selected choices are valid.
                    # (E.g., CYLINDER as part of pg.Shape)
                    pg.util.check_enum_key(
                        enum_class=class_attr.property_enum_class,
                        key=instance_attr,
                        param_name=attr_name,
                    )
                if isinstance(class_attr, prop.ComponentReferenceProperty):
                    # Ensure that referenced components exist.
                    if (
                        not class_attr.property_can_be_empty(self)
                        and instance_attr == ""
                    ):
                        raise ValueError(
                            f"Tried to set {attr_name} on "
                            f"{self.component_name}: "
                            "Value must not be empty!"
                        )
                    if (
                            not class_attr.property_can_be_empty(self)
                            and instance_attr != ""
                            and instance_attr
                            not in simulation_kernel.get_components()
                    ):
                        raise ValueError(
                            f"Tried to set {attr_name} on "
                            f"{self.component_name}: "
                            "No component with the name "
                            f"{instance_attr} attached to the simulation "
                            "kernel could be found."
                        )
                if isinstance(class_attr, prop.VectorProperty):
                    # Ensure vectors are valid:
                    pg.util.check_vector(
                        value=instance_attr,
                        component_name=self.component_name,
                        key=attr_name,
                    )

    def process_new_time_step(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            notification_stage: 'pg.NotificationStages',
    ):
        pass

    def finalize(self, simulation_kernel: 'pg.SimulationKernel'):
        pass
