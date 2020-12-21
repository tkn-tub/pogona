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
import ruamel.yaml
import pogona as pg


def test_update_dict_recursively():
    a = dict(
        components=dict(
            sensor_a='hello',
            injector=dict(x=1337, y=3.141, z='ignore'),
        ),
        seed=42,
    )
    b = dict(
        components=dict(
            uninherit=['sensor_a'],  # don't add sensor_a
            injector=dict(
                x=1337,
                y=3,
                uninherit=['y'],  # don't update y
            )
        ),
        seed=43,  # should not be overwritten
    )
    pg.update_dict_recursively(
        to_update=a,
        to_read=b,  # has precedence
        uninherit=True,
    )
    assert a == dict(
        components=dict(
            injector=dict(x=1337, y=3, z='ignore'),
        ),
        seed=43,
    )


def test_assemble_config_recursively():
    yaml = ruamel.yaml.YAML(typ='safe')
    expected_result_path = os.path.join(
        os.path.dirname(__file__),
        "a_b_override.yaml"
    )
    b_path = os.path.join(
        os.path.dirname(__file__),
        "b.yaml"
    )
    with open(expected_result_path, 'r') as fh:
        expected = yaml.load(fh)

    result = pg.assemble_config_recursively(
        conf=b_path,  # inherits from a.yaml
        # Add some override parameters as one might add via the command
        # line argument --param:
        override_conf=dict(
            components=dict(
                uninherit=['other_component_to_uninherit'],
                component_u=dict(
                    uninherit=['value'],
                    new_value=42
                )
            ),
            uninherit=['global_val_to_uninherit'],
            global_z=3,
        ),
    )
    assert result == expected


def test_args_config_params_to_dict():
    params = [
        'x=42',
        'components.injector.jitter=lots',
        'components.injector.particles=\'shaped like stars\''
    ]
    result = pg.args_config_params_to_dict(params)
    assert result == dict(
        x=42,
        components=dict(injector=dict(
            jitter='lots',
            particles='shaped like stars',
        ))
    )
