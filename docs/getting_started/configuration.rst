.. |nbsp| unicode:: 0xA0
   :trim:

.. _configuration:

Configuration
=============

Pogona simulations can be configured with YAML files.
You can find the available options and :class:`~pogona.Component` instances in the :ref:`API documentation <apidoc>`.

Inheriting the Scene
--------------------

First, let us have a look at the partial configuration file that we already generated in the :ref:`previous step <scene_config>`.
The following is what the first couple of lines of may look like:

.. literalinclude:: ../../examples/linked-tubes/linked-tubes.scene.yaml
    :language: yaml
    :linenos:
    :lines: 1-27

At the top level, you can see that below the key ``components`` are listed all the Pogona components we added to the Blender scene, and each component has defined a ``translation``, ``rotation``, ``scale``, as well as a shape and visualization scale.
These parameters already have the correct names to be passed to instances of :class:`pogona.Component`.

To configure the remainder of our simulation scenario, we would technically be able to simply edit the file ``linked-tubes.scene.yaml`` and pass this configuration file to the Pogona simulator.
However, if we ever discover that we might want to adjust the 3D scene of this scenario, we would have to either overwrite this file using the Blender add-on or edit it manually. [#f1]_
Instead, create a new file and name it ``linked-tubes.config.yaml``.
Keeping the scene separate from the remaining configuration will also help us to reduce configuration clutter.

Start the new file as follows:

.. code-block:: yaml
    :linenos:

    inherit:
      - linked-tubes.scene.yaml


In lines 1 and 2 we specify that we want to inherit from our scene configuration file.
The ``inherit`` directive can be used in any Pogona configuration file to include other configuration files with a path relative to the inheriting file.

.. [#f1] It would technically also be possible to extend the Blender add-on to merge exported configurations with an existing configuration, but since configurations are Python ``dict``-based, this may change the order of items or strip the configuration of comments if not properly implemented.

Configuring the Simulation Kernel
---------------------------------

Now extend the configuration as follows:

.. code-block:: yaml
    :linenos:

    inherit:
      - linked-tubes.scene.yaml
    seed: 42
    sim_time_limit: 15
    base_delta_time: 0.005
    use_adaptive_time_stepping: True
    adaptive_time_max_error_threshold: 1e-7
    movement_predictor:
        integration_method: RUNGE_KUTTA_FEHLBERG_45

The parameters in lines 3–7 configure the :class:`~pogona.SimulationKernel`, with each key corresponding to any class attribute that is a subclass of :class:`~pogona.properties.AbstractProperty`:

* ``seed`` specifies a random seed that will be used whenever random values are needed, unless the respective component is configured to use its own random seed.
* ``sim_time_limit`` says that our simulation should end after 15 |nbsp| s.
* ``base_delta_time`` defines the step size.
  Every 5 |nbsp| ms, all :class:`~pogona.Sensor` instances will have a chance to react to all particles.
  If we do not use adaptive time stepping, ``base_delta_time`` also corresponds to the step size with which the positions of particles will be updated.
* ``use_adaptive_time_stepping: True`` specifies that we *do* want to use adaptive time stepping in this simulation.
* ``adaptive_time_max_error_threshold`` is the maximum integration error we want to tolerate when using adaptive time stepping.
  The step size will be adjusted accordingly.

Finally, ``movement_predictor`` contains the settings for the 'kernel component' :class:`~pogona.MovementPredictor`.
All existing kernel components are listed in the documentation of the :class:`~pogona.SimulationKernel`.
In this case, we need to override the default setting of the ``integration_method`` to an :class:`~pogona.Integration` method that supports adaptive time stepping.

Configuring Simulation Components
---------------------------------

Next, we need to configure the components that so far only exist in our scene as empty husks.
To do this, copy the names of all components defined in ``linked-tubes.scene.yaml`` into the ``components`` block in ``linked-tubes.config.yaml``:

.. code-block:: yaml
    :linenos:

    inherit:
      - linked-tubes.scene.yaml
    seed: 42
    sim_time_limit: 15
    base_delta_time: 0.005
    use_adaptive_time_stepping: True
    adaptive_time_max_error_threshold: 1e-7
    movement_predictor:
      integration_method: RUNGE_KUTTA_FEHLBERG_45
    components:
      destructor:
        type: SensorDestructing
      injector:
        type: Injector
      sensor:
        type: SensorEmpirical
      tube0:
        type: ObjectTube
      tube1:
        type: ObjectTube

Besides the component names, you will notice that the version of the configuration file above also includes a ``type`` for each component, which corresponds to the name of the respective :class:`~pogona.Component` subclass.
Like the configuration of the :class:`~pogona.SimulationKernel`, each component can also be configured using the names of :class:`~pogona.properties.AbstractProperty`-based class attributes of each :class:`~pogona.Component` subclass.
You can find an example of a complete configuration at the bottom of this page.

:destructor:
    This component does not require any additional configuration.
    By default, any particle entering its region will be removed from the simulation.
:injector:
    The injector needs a number of particles to inject and a reference to the :class:`~pogona.Object` that newly spawned particles will be associated with:

    .. code-block:: yaml

        injector:
          type: Injector
          injection_amount: 5  # particles in each base time step (cp. `modulation`)
          attached_object: tube0
:sensor:
    :class:`~pogona.SensorEmpirical` needs a subfolder name in the output directory where it will store its sensor logs.
    Additionally, we can specify a sensor model, which in this case maps the relative position of particles inside the sensor to a magnetic susceptibility response.
    In :ref:`the scene configuration <scene_config>`, we already made sure that the dimensions of our sensor match this sensor model choice.

    .. code-block:: yaml

        sensor:
          type: SensorEmpirical
          log_folder: sensor_data  # relative to `--results-dir`
          use_known_sensor: ERLANGEN_20200310
:tube0, tube1:
    As explained in the chapter for :ref:`the scene configuration <scene_config>`, we cannot use the regular ``scale`` parameter for vector fields such as our ``tube0`` and ``tube1``, because vector fields typically already have the correct scale.
    However, the :class:`~pogona.objects.ObjectTube` class still allows us to choose the *length* of the tube.
    Internally, the instance of this class will then load the smallest available tube vector field that our tube would fit into.
    Additionally, we need to define the flow rate and mesh resolution, which are used to compose the final OpenFOAM simulation results path from which the vector field will be loaded.

    .. code-block:: yaml

        tube0:
          type: ObjectTube
          radius: 0.00076  # in m
          length: 0.09  # in m
          flow_rate: 10  # in ml/min
          mesh_resolution: 11  # radius cells in OpenFOAM mesh definition
        tube1:
          type: ObjectTube
          radius: 0.00076  # in m
          length: 0.09  # in m
          flow_rate: 10  # in ml/min
          mesh_resolution: 11  # radius cells in OpenFOAM mesh definition

With all components from our 3D scene taken care of, there are a few further, dimensionless components we need to add.

* We already have an :class:`~pogona.Injector`, but we have not yet specified when and how injections should take place.
  We can use on-off keying, using a :class:`~pogona.ModulationOOK` instance, to transmit a bit sequence from a :class:`~pogona.BitstreamGenerator`.

  .. code-block:: yaml

      modulation:
        type: ModulationOOK
        pause_duration: 1.5  # in s
        attached_injector: injector
        attached_pump: pump
        # Inject new particles in every time step while active,
        # rather than all at once:
        use_burst: False
      bitstream_generator:
        type: BitstreamGenerator
        start_time: 0  # in s
        bit_sequence: "101001"
        attached_modulation: modulation

* When using vector fields in a Pogona simulation, each particle will typically always be associated with exactly one :class:`~pogona.Object`.
  When particles leave ``tube0``, we need to make sure that their respective association is handed over to ``tube1``.
  This is done with a :class:`~pogona.SensorTeleporting`, that checks if a particle is within the :attr:`ObjectTube's outlet_zone <pogona.objects.ObjectTube.outlet_zone>`.
  Furthermore, each :class:`~pogona.Object` defines its own set of inlets and outlets, since some objects may have multiple of each.
  We have to specify the name of the inlet and outlet for the link between our two tubes.
  This is not critical in the present example, but it is required if we have a simulation scenario in which the flow rate might change in ``tube0`` and if this change should propagate to ``tube1``.
  If we had a separate inlet for the particle injections in which we wanted to stop the flow whenever the pump is inactive, we would need another teleporter from the pump to the respective tube.

  .. code-block:: yaml

      teleport_tube0_to_tube1:
        type: SensorTeleporting
        source_object: tube0
        target_object: tube1
        source_outlet_name: outlet
        target_inlet_name: inlet

* Lastly, we want to log all particle positions in each base time step for later visualization, and we want see some status information like the current number of particles in the terminal output:

  .. code-block:: yaml

      plotter_terminal:
        type: PlotterTerminal
      plotter_csv:
        type: PlotterCSV
        folder: particle_positions  # relative to --results-dir
        write_interval: 1  # in number of time steps

Complete Configuration
----------------------

.. literalinclude:: ../../examples/linked-tubes/linked-tubes.config.yaml
    :language: yaml
    :linenos:

Having now configured our simulation scenario, we can go ahead and run it.
