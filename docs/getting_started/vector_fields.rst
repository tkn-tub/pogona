Vector Fields
=============

Each :class:`~pogona.Object` that is based on a vector field, like an :class:`~pogona.object.ObjectTube` or :class:`~pogona.object.ObjectYPiece`, expects OpenFOAM simulation results in an exact folder structure relative to the path passed to the simulator with the command line argument ``--openfoam-cases-path``.
For details on what exactly a certain OpenFOAM simulation result folder is expected to be named, refer to the documentation for :class:`pogona.Object` and that of the respective subclass.

In order to run the example scenarios, make sure to have a copy of our `OpenFOAM cases repository <https://github.com/tkn-tub/pogona-openfoam-cases>`_ and that the relevant OpenFOAM simulations have completed successfully.
