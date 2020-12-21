pogona.SimulationKernel
=======================

.. currentmodule:: pogona

.. autoclass:: SimulationKernel
   :members:
   :show-inheritance:
   :inherited-members:

   
   
   .. rubric:: Attributes

   .. autosummary::
   
      ~SimulationKernel.adaptive_time_corrections_limit
      ~SimulationKernel.adaptive_time_max_error_threshold
      ~SimulationKernel.adaptive_time_safety_factor
      ~SimulationKernel.base_delta_time
      ~SimulationKernel.component_name
      ~SimulationKernel.interpolation_method
      ~SimulationKernel.results_dir
      ~SimulationKernel.seed
      ~SimulationKernel.sim_time
      ~SimulationKernel.sim_time_limit
      ~SimulationKernel.use_adaptive_time_stepping
   
   

   
   .. automethod:: __init__

   
   .. rubric:: Methods

   .. autosummary::
   
      ~SimulationKernel.__init__
      ~SimulationKernel.attach_component
      ~SimulationKernel.destroy_molecule
      ~SimulationKernel.finalize
      ~SimulationKernel.get_base_delta_time
      ~SimulationKernel.get_components
      ~SimulationKernel.get_elapsed_base_time_steps
      ~SimulationKernel.get_elapsed_sub_time_steps
      ~SimulationKernel.get_integration_method
      ~SimulationKernel.get_interpolation_method
      ~SimulationKernel.get_mesh_manager
      ~SimulationKernel.get_molecule_manager
      ~SimulationKernel.get_movement_predictor
      ~SimulationKernel.get_random_number_generator
      ~SimulationKernel.get_scene_manager
      ~SimulationKernel.get_seed
      ~SimulationKernel.get_sensor_manager
      ~SimulationKernel.get_simulation_time
      ~SimulationKernel.initialize
      ~SimulationKernel.initialize_components
      ~SimulationKernel.notify_components_new_time_step
      ~SimulationKernel.process_new_time_step
      ~SimulationKernel.set_arguments
      ~SimulationKernel.simulation_loop_adaptive_rkf
      ~SimulationKernel.simulation_loop_legacy
      ~SimulationKernel.start
   
   