Installation
============

:ref:`Download <download>` the Pogona sources.
Make sure you have an up-to-date version of Python installed, as well as the Python package ``pipenv``.
Then, use Pipenv to create a virtual environment and to install all dependencies like so:

.. code-block:: bash

    pipenv install --dev

Afterwards, you can enter the virtual environment with the command ``pipenv shell``.
Run the following to confirm that Pogona is installed:

.. code-block:: bash

    pogona -h
