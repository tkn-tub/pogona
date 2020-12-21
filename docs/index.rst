.. pogona documentation master file, created by
   sphinx-quickstart on Tue Dec 17 12:16:12 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pogona Documentation
======================

What Is the Pogona Simulator?
-----------------------------

The Pogona simulator has been developed as part of a research project funded by the German Ministry of Education and Research (BMBF) on macroscopic molecular communication [1]_.
The underlying idea is to use a computational fluid dynamics (CFD) simulator to pre-compute a vector field.
Pogona then reads this vector field and simulates the movement of particles by making the particles follow the flow speed vectors.

If you use Pogona in your own work, we would appreciate a citation:

  J. P. Drees, L. Stratmann, F. Bronner, M. Bartunik, J. Kirchner, H. Unterweger, and F. Dressler, “Efficient Simulation of Macroscopic Molecular Communication: The Pogona Simulator,” in 7th ACM International Conference on Nanoscale Computing and Communication (NANOCOM 2020). Virtual Conference: ACM, Sep. 2020.
  `[DOI] <http://dx.doi.org/10.1145/3411295.3411297>`_ `[BibTeX] <https://www2.tkn.tu-berlin.de/bib/drees2020efficient/drees2020efficient.bib>`_ `[PDF and details] <https://www2.tkn.tu-berlin.de/bib/drees2020efficient/>`_

.. [1] `MAMOKO project webpage on the website of TU Berlin <https://www2.tkn.tu-berlin.de/projects/mamoko/>`_

.. _download:

Where to Get It
---------------

**TODO** GitHub links to repos: Pogona, Cases, Blender add-on (and more example simulations?)

Contents
--------

.. toctree::
   :maxdepth: 2

   getting_started/index

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
