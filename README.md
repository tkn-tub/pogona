# Pogona – Simulation of Macroscopic Molecular Communication

## What Is the Pogona Simulator?

The Pogona simulator has been developed as part of a research project funded by the German Ministry of Education and Research (BMBF) on macroscopic molecular communication [1].
The underlying idea is to use a computational fluid dynamics (CFD) simulator to pre-compute a vector field.
Pogona then reads this vector field and simulates the movement of particles by making the particles follow the flow speed vectors.

If you use Pogona in your own work, we would appreciate a citation:

> J. P. Drees, L. Stratmann, F. Bronner, M. Bartunik, J. Kirchner, H. Unterweger, and F. Dressler, “Efficient Simulation of Macroscopic Molecular Communication: The Pogona Simulator,” in 7th ACM International Conference on Nanoscale Computing and Communication (NANOCOM 2020). Virtual Conference: ACM, Sep. 2020.
> [[DOI]](http://dx.doi.org/10.1145/3411295.3411297) [[BibTeX]](https://www2.tkn.tu-berlin.de/bib/drees2020efficient/drees2020efficient.bib) [[PDF and details]](https://www2.tkn.tu-berlin.de/bib/drees2020efficient/)

[1] [MAMOKO project webpage on the website of TU Berlin](https://www2.tkn.tu-berlin.de/projects/mamoko/)

## Basic Usage

Please also read the [full Pogona documentation](https://pogona.readthedocs.io/en/latest/).

You will need at least Python 3.8 installed on your system.

In the folder of this README, use pipenv to install all requirements:
```bash
pipenv install --dev
```
You can then enter the virtualenv with the following command:
```bash
pipenv shell
# You can later deactivate the virtualenv like so:
exit
```

Before you can run a simulation, be sure to have all CFD **simulation results** ready that are required by the particular simulation configuration.
Please refer to our [OpenFOAM cases](https://github.com/tkn-tub/pogona-openfoam-cases) repository for details.

The second important requirement is the **simulation configuration** itself.
Refer to the [Pogona documentation](https://pogona.readthedocs.io/en/latest/) on how to create your own configuration or use one of our example scenarios (coming soon).

To run a simulation, run
```bash
pogona --openfoam-cases-path /path/to/openfoam/cases --config /path/to/config.yaml --results-dir /path/to/output/folder/
```

To see all available command line arguments, run `pogona -h`.
