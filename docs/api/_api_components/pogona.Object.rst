pogona.Object
=============

.. currentmodule:: pogona

.. autoclass:: Object
   :members:
   :show-inheritance:
   :inherited-members:

   
   
   .. rubric:: Attributes

   .. autosummary::
   
      ~Object.component_name
      ~Object.dummy_boundary_points
      ~Object.is_active
      ~Object.object_id
      ~Object.openfoam_cases_path
      ~Object.rotation
      ~Object.scale
      ~Object.translation
      ~Object.use_sensor_subscriptions
      ~Object.walls_patch_names
   
   

   
   .. automethod:: __init__

   
   .. rubric:: Methods

   .. autosummary::
   
      ~Object.__init__
      ~Object.finalize
      ~Object.find_latest_time_step
      ~Object.get_closest_cell_centre_id
      ~Object.get_current_mesh_global
      ~Object.get_current_mesh_local
      ~Object.get_fallback_mesh_index
      ~Object.get_flow
      ~Object.get_mesh_index
      ~Object.get_outlet_area
      ~Object.get_path
      ~Object.get_transformation
      ~Object.get_vector_field_manager
      ~Object.initialize
      ~Object.load_current_vector_field
      ~Object.process_changed_inlet_flow_rate
      ~Object.process_new_time_step
      ~Object.set_arguments
   
   