pogona.objects.ObjectPumpTimed
==============================

.. currentmodule:: pogona.objects

.. autoclass:: ObjectPumpTimed
   :members:
   :show-inheritance:
   :inherited-members:

   
   
   .. rubric:: Attributes

   .. autosummary::
   
      ~ObjectPumpTimed.component_name
      ~ObjectPumpTimed.dummy_boundary_points
      ~ObjectPumpTimed.flow_rate
      ~ObjectPumpTimed.injection_flow_mlpmin
      ~ObjectPumpTimed.is_active
      ~ObjectPumpTimed.name
      ~ObjectPumpTimed.object_id
      ~ObjectPumpTimed.openfoam_cases_path
      ~ObjectPumpTimed.pump_duration_s
      ~ObjectPumpTimed.rotation
      ~ObjectPumpTimed.scale
      ~ObjectPumpTimed.translation
      ~ObjectPumpTimed.use_sensor_subscriptions
      ~ObjectPumpTimed.walls_patch_names
   
   

   
   .. automethod:: __init__

   
   .. rubric:: Methods

   .. autosummary::
   
      ~ObjectPumpTimed.__init__
      ~ObjectPumpTimed.finalize
      ~ObjectPumpTimed.find_latest_time_step
      ~ObjectPumpTimed.get_closest_cell_centre_id
      ~ObjectPumpTimed.get_current_mesh_global
      ~ObjectPumpTimed.get_current_mesh_local
      ~ObjectPumpTimed.get_fallback_mesh_index
      ~ObjectPumpTimed.get_flow
      ~ObjectPumpTimed.get_mesh_index
      ~ObjectPumpTimed.get_outlet_area
      ~ObjectPumpTimed.get_path
      ~ObjectPumpTimed.get_transformation
      ~ObjectPumpTimed.get_vector_field_manager
      ~ObjectPumpTimed.initialize
      ~ObjectPumpTimed.load_current_vector_field
      ~ObjectPumpTimed.process_changed_inlet_flow_rate
      ~ObjectPumpTimed.process_new_time_step
      ~ObjectPumpTimed.set_arguments
      ~ObjectPumpTimed.set_interpolation_method
      ~ObjectPumpTimed.start_injection
   
   