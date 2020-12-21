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

import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

with open("version.txt", "r") as fh:
    version = fh.read().strip()

setuptools.setup(
    name="pogona",
    version=version,
    author="Data Communications and Networking (TKN), TU Berlin",
    author_email="stratmann@ccs-labs.org",
    description="The Pogona simulator for macroscopic molecular communication",
    long_description=long_description,
    url="https://git.cs.upb.de/mamoko/mamoko",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            "pogona = pogona:start_cli"
        ],
    },
    install_requires=[
        "openfoamparser",
        "numpy",
        "ruamel.yaml",
        "coloredlogs",
        "argparse",
        "scipy",
    ],
)
