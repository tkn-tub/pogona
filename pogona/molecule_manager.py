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

from typing import List
import copy

import pogona as pg
import pogona.properties as prop


class MoleculeManager(pg.Component):
    update_molecule_collection_immediately = prop.BoolProperty(
        False,
        required=False,
    )
    """
    If True, adding or deleting a molecule will happen immediately
    when `add_molecule` or `destroy_molecule` is called.

    However, since such calls usually happen while the collection
    of molecules is being iterated over, and because changing a collection
    while iterating over it may cause problems, we can alternatively
    collect all molecules to add and all molecules to delete in
    temporary lists.
    Since we can assume these temporary lists to be much smaller than
    the total number of molecules in each time step, which would have
    to be copied otherwise in each step, this should give us a
    performance benefit.

    If False, make sure to call `apply_changes` at the end of each
    time step.
    """

    def __init__(self):
        super().__init__()

        self._molecules = dict()
        self._total_counter = 0
        self._molecules_to_add: List['pg.Molecule'] = []
        self._molecules_to_destroy: List['pg.Molecule'] = []

    def initialize(
            self,
            simulation_kernel: 'pg.SimulationKernel',
            init_stage: 'pg.InitStages'
    ):
        super().initialize(
            simulation_kernel=simulation_kernel,
            init_stage=init_stage
        )

    def add_molecule(self, molecule):
        if self.update_molecule_collection_immediately:
            molecule.id = self._total_counter
            self._total_counter += 1
            self._molecules[molecule.id] = molecule
        else:
            self._molecules_to_add.append(molecule)

    def get_all_molecules(self):
        return self._molecules

    def get_all_molecule_copies(self):
        return copy.deepcopy(self._molecules)

    def update_molecule(self, molecule):
        """
        Replace an existing molecule with an updated molecule with the same ID.

        :param molecule:
        :return:
        """
        # This temporary list would be as long as the total number of
        # molecules if we were to consider this method for
        # `update_molecule_collection_immediately`.
        # However, replacing a dict item does not seem to cause any trouble
        # while iterating over the same dict.
        self._molecules[molecule.id] = molecule

    def destroy_molecule(self, molecule):
        if self.update_molecule_collection_immediately:
            self._molecules.pop(molecule.id)
        else:
            self._molecules_to_destroy.append(molecule)

    def apply_changes(self):
        """
        Apply any pending molecule insertions and deletions.

        This should be called after every time step if
        `update_molecule_collection_immediately` is False.
        """
        # Process the deletions first for memory efficiency…
        for molecule in self._molecules_to_destroy:
            self._molecules.pop(molecule.id)
        for molecule in self._molecules_to_add:
            molecule.id = self._total_counter
            self._total_counter += 1
            self._molecules[molecule.id] = molecule
        self._molecules_to_destroy.clear()
        self._molecules_to_add.clear()
