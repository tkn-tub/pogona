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

"""
Properties for Components.
Assign instances of these to class attributes.
The Component base class will automatically convert these to instance
variables in __init__.

This solution makes several things possible:
- Our Blender add-on can parse all properties of all Components without
having to create instances.
- Code readability: It is easy to see what the default value of a variable
is and whether or not it is required.
- Anything that can be defined in YAML files is now an AbstractProperty.
- Code completion in IDEs is still possible.
- EnumProperty makes validation easier if only a limited set of choices is
allowed.
"""

from typing import Any, Type, Callable, Union
import enum

import pogona as pg


class AbstractProperty:
    def __new__(cls, default: Any, required: bool, *args, **kwargs):
        """

        :param default:
        :param required: If True, this property must be user-configured (i.e.,
            the default value is irrelevant).
        :param args:
        :param kwargs:
        """
        x = super().__new__(cls, default)
        x.required = required
        return x


class IntProperty(AbstractProperty, int):
    pass  # intentional


class BoolProperty(AbstractProperty, int):
    # Python doesn't allow subclassing bool; using this workaround:
    # https://jfine-python-classes.readthedocs.io/en/latest/subclass-int.html
    def __new__(cls, default, required: bool, *args, **kwargs):
        return super().__new__(
            cls,
            default=bool(default),
            required=required,
            *args,
            **kwargs,
        )

    def __repr__(self):
        return ['False', 'True'][self]  # (self is an int)


class StrProperty(AbstractProperty, str):
    pass  # intentional


class FloatProperty(AbstractProperty, float):
    pass  # intentional


class FloatArrayProperty(AbstractProperty, list):
    """
    Reserved for lists of floats of arbitrary lengths.
    For vectors of length 3 use VectorProperty (has additional checks
    in Component.initialize).
    """
    pass  # intentional


class VectorProperty(AbstractProperty, list):
    """
    Reserved for lists of floats of length 3.
    Validated in Component.initialize.
    """
    pass  # intentional


class ListOfVectorsProperty(AbstractProperty, list):
    """
    List of length-3 lists of floats.
    """
    pass  # intentional, for now


class EnumProperty(AbstractProperty, str):
    def __new__(
            cls,
            default: str,
            name: str,
            required: bool,
            enum_class: Type[enum.Enum],
            *args,
            **kwargs,
    ):
        """
        :param default:
        :param name: Name of this property. Only used in an error message in
            case the default value is invalid.
        :param required:
        :param enum_class:
        :param args:
        :param kwargs:
        """
        pg.util.check_enum_key(
            enum_class=enum_class,
            key=default,
            param_name=name,
        )
        x = super().__new__(cls, default, required, *args, **kwargs)
        x.property_name = name
        x.property_enum_class = enum_class
        return x
    # TODO: can we make this behave as Enum instead of as str without
    #  breaking config files?


class ComponentReferenceProperty(AbstractProperty, str):
    def __new__(
            cls,
            default: str,
            required: bool,
            can_be_empty: 'Union[bool, Callable[[pg.Component], bool]]',
            *args,
            **kwargs,
    ):
        """
        :param default:
        :param required: If True, this property must be user-configured (i.e.,
            the default value is irrelevant).
        :param can_be_empty: If True, a user may override the default
            value with an empty string.
        :param args:
        :param kwargs:
        """
        x = super().__new__(cls, default, required, *args, **kwargs)
        if callable(can_be_empty):
            x.property_can_be_empty = can_be_empty
        else:
            x.property_can_be_empty = lambda component: can_be_empty
        return x
