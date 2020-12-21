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
from typing import Dict, Union, Optional
import logging
import ruamel.yaml

LOG = logging.getLogger(__name__)


def update_dict_recursively(
        to_update: Dict,
        to_read: Dict,
        uninherit=True,
        clear_uninherit=True,
):
    """
    :param to_update: Dictionary to update in-place.
    :param to_read: Dictionary to use for updating. Will be changed in the
        process! Has precedence over to_update!
    :param uninherit: Allow removing items from the old dict;
        example: 'a' will be removed:
        d_old={'a': 42, 'b': 2}, d_new={'b': 3, 'uninherit': ['a']}
        -> {'b': 3}
    :param clear_uninherit: If False, lists of keys to uninherit will not
        be cleared. This can be useful for multiple inheritance
        where the same 'uninherit' should be applied to multiple configs.
    """
    if uninherit:
        # to_read has precedence over to_update
        # -> to_read may define things it does not want to inherit from
        #    to_update, i.e., things it wants to 'uninherit'
        keys_to_uninherit = to_read.get('uninherit', [])
        if isinstance(keys_to_uninherit, str):
            keys_to_uninherit = [keys_to_uninherit]
        for key_to_uninherit in keys_to_uninherit:
            to_update.pop(key_to_uninherit, None)
        if clear_uninherit:
            to_read.pop('uninherit', None)

    # The actual updating:
    recursively_updated_dict_keys = []
    for k, v in to_read.items():
        # Look for dictionaries that need to be updated recursively
        if k not in to_update:
            continue
        if not isinstance(v, dict) or not isinstance(to_update[k], dict):
            # Example: A dict can be replaced by a str.
            continue
        update_dict_recursively(
            to_update=to_update[k],
            to_read=v,
            uninherit=uninherit,
        )
        recursively_updated_dict_keys.append(k)
    for k in recursively_updated_dict_keys:
        # Prevent the new dict from replacing the old one:
        to_read.pop(k)
    # Update the remaining dict as usual:
    to_update.update(to_read)


def clear_uninherits(d: Dict):
    """Remove all remaining items with key 'uninherit'."""
    d.pop('uninherit', None)
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        clear_uninherits(v)


def assemble_config_recursively(
        conf: Union[str, Dict],
        base_path: str = None,
        override_conf: Optional[Dict] = None,
) -> Dict:
    """
    :param conf: Either the filename of a YAML config file or a dictionary
        of one that has already been loaded.
    :param base_path: Only required if conf is not a filename.
        Path relative to which to search for inherited configuration files.
    :param override_conf: If given, update the original configuration
        given with `conf` after all other files have been inherited from.
    """
    if isinstance(conf, str):
        # Will only happen in the first call, if at all;
        # not in recursive calls.
        # Load from file:
        base_path = os.path.dirname(conf)
        with open(conf, 'r') as fh:
            yaml = ruamel.yaml.YAML(typ='safe')
            conf = yaml.load(fh)
    elif base_path is None:
        raise ValueError("base_path must not be None if conf is a dict!")

    inherited_conf_filenames = conf.pop('inherit', [])
    if isinstance(inherited_conf_filenames, str):
        inherited_conf_filenames = [inherited_conf_filenames]
    for filename_rel_to_conf in inherited_conf_filenames:
        inherited_conf_filename = os.path.join(base_path, filename_rel_to_conf)
        LOG.debug(f"Inheriting from '{inherited_conf_filename}'="
                  f"'{os.path.abspath(inherited_conf_filename)}'.")
        with open(inherited_conf_filename, 'r') as fh:
            yaml = ruamel.yaml.YAML(typ='safe')
            inherited_conf = yaml.load(fh)
        inherited_conf = assemble_config_recursively(
            conf=inherited_conf,
            base_path=os.path.dirname(inherited_conf_filename),
            override_conf=None,
        )
        update_dict_recursively(
            to_update=inherited_conf,
            to_read=conf,  # takes precedence over inherited_conf
            uninherit=True,
            clear_uninherit=False,
            # ^ 'uninherit' must be available for all inherited configs
        )
        conf = inherited_conf

    if override_conf is not None:
        update_dict_recursively(
            to_update=conf,
            to_read=override_conf,
            uninherit=True,
            clear_uninherit=True
        )
    clear_uninherits(conf)
    return conf


def write_config(conf: dict, filename):
    with open(filename, 'w') as fh:
        yaml = ruamel.yaml.YAML(typ='safe')
        yaml.default_flow_style = False
        yaml.dump(conf, fh)
