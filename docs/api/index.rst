.. _apidoc:

Pogona API Documentation
========================

.. currentmodule:: pogona

Core
----

.. autosummary::
    :toctree: _api_core
    :template: custom-class-template.rst

    Face
    EmbeddedRungeKuttaMethod
    Geometry
    InitStages
    Integration
    Interpolation
    KnownSensors
    MeshManager
    Molecule
    MoleculeManager
    MovementPredictor
    NotificationStages
    RKFehlberg45
    SceneManager
    Shapes
    SensorManager
    SensorSubscriptionsUsage
    SimulationKernel
    Transformation
    VectorField
    VectorFieldParser

Components
----------

.. autosummary::
    :toctree: _api_components
    :template: custom-class-template.rst

    BitstreamGenerator
    Component
    Injector
    Modulation
    ModulationOOK
    ModulationPPM
    Object
    PlotterCSV
    PlotterTerminal
    Sensor
    SensorCounting
    SensorDestructing
    SensorEmpirical
    SensorEmpiricalRadialTest
    SensorFlowRate
    SensorTeleporting
    SprayNozzle

Objects
^^^^^^^

.. currentmodule:: pogona.objects

.. autosummary::
    :toctree: _api_objects
    :template: custom-class-template.rst

    ObjectPumpPeristaltic
    ObjectPumpTimed
    ObjectTube
    ObjectTubeAnalytical
    ObjectYPiece

Properties
----------

.. currentmodule:: pogona.properties

.. autosummary::
    :toctree: _api_properties
    :template: custom-class-template.rst

    AbstractProperty
    BoolProperty
    ComponentReferenceProperty
    EnumProperty
    FloatArrayProperty
    FloatProperty
    IntProperty
    ListOfVectorsProperty
    StrProperty
    VectorProperty

Utility Functions
-----------------

.. currentmodule:: pogona

.. autosummary::
    :toctree: _api_misc

    assemble_config_recursively
    update_dict_recursively
    write_config

.. autosummary::
    :toctree: _api_util
    :template: custom-module-template.rst
    :recursive:

    util
