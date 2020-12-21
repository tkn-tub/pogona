pogona.objects.ObjectTube
=========================

.. currentmodule:: pogona.objects

.. autoclass:: ObjectTube
   :members:
   :show-inheritance:
   :inherited-members:

   
   
   .. rubric:: Attributes

   .. autosummary::
   
      ~ObjectTube.component_name
      ~ObjectTube.dummy_boundary_points
      ~ObjectTube.fallback_flow_rate
      ~ObjectTube.flow_rate
      ~ObjectTube.inlet_zone
      ~ObjectTube.is_active
      ~ObjectTube.length
      ~ObjectTube.mesh_resolution
      ~ObjectTube.name
      ~ObjectTube.object_id
      ~ObjectTube.openfoam_cases_path
      ~ObjectTube.outlet_zone
      ~ObjectTube.radius
      ~ObjectTube.rotation
      ~ObjectTube.scale
      ~ObjectTube.translation
      ~ObjectTube.use_sensor_subscriptions
      ~ObjectTube.variant
      ~ObjectTube.walls_patch_names
   
   

   
   .. automethod:: __init__

   
   .. rubric:: Methods

   .. autosummary::
   
      ~ObjectTube.__init__
      ~ObjectTube.finalize
      ~ObjectTube.find_latest_time_step
      ~ObjectTube.get_closest_cell_centre_id
      ~ObjectTube.get_current_mesh_global
      ~ObjectTube.get_current_mesh_local
      ~ObjectTube.get_fallback_mesh_index
      ~ObjectTube.get_flow
      ~ObjectTube.get_mesh_index
      ~ObjectTube.get_outlet_area
      ~ObjectTube.get_path
      ~ObjectTube.get_transformation
      ~ObjectTube.get_tube_mesh_index
      ~ObjectTube.get_vector_field_manager
      ~ObjectTube.initialize
      ~ObjectTube.load_current_vector_field
      ~ObjectTube.process_changed_inlet_flow_rate
      ~ObjectTube.process_new_time_step
      ~ObjectTube.set_arguments
   
   