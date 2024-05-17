from django.urls import path
from .views import other_views
from .views import question_views
from .views import smart_search_views

urlpatterns=[
    path("health", other_views.get_health),
    path("get_current_user", other_views.get_current_user),
    path("available_organizations", other_views.get_available_organizations),
    path("dataset", other_views.get_dataset),
    path("available_datasets", other_views.get_available_datasets),
    path("add_search_history_item", other_views.add_search_history_item),
    path("get_search_history", other_views.get_search_history),
    path("add_collection", other_views.add_collection),
    path("add_collection_class", other_views.add_collection_class),
    path("delete_collection_class", other_views.delete_collection_class),
    path("get_collections", other_views.get_collections),
    path("get_collection", other_views.get_collection),
    path("get_trained_classifier", other_views.get_trained_classifier),
    path("set_trained_classifier", other_views.set_trained_classifier),
    path("get_collection_items", other_views.get_collection_items),
    path("delete_collection", other_views.delete_collection),
    path("add_item_to_collection", other_views.add_item_to_collection),
    path("remove_collection_item", other_views.remove_collection_item),
    path("remove_collection_item_by_value", other_views.remove_collection_item_by_value),
    path("add_stored_map", other_views.add_stored_map),
    path("get_stored_maps", other_views.get_stored_maps),
    path("stored_map_data", other_views.get_stored_map_data),
    path("delete_stored_map", other_views.delete_stored_map),
    path("get_generators", other_views.get_generators),
    path("create_chat_from_search_settings", question_views.create_chat_from_search_settings),
    path("add_collection_class_chat", question_views.add_collection_class_chat),
    path("add_chat_question", question_views.add_chat_question),
    path("get_chats", question_views.get_chats),
    path("get_collection_class_chats", question_views.get_collection_class_chats),
    path("get_chat_by_id", question_views.get_chat_by_id),
    path("add_collection_column", question_views.add_collection_column),
    path("delete_collection_column", question_views.delete_collection_column),
    path("set_collection_cell_data", question_views.set_collection_cell_data),
    path("extract_question_from_collection_class_items", question_views.extract_question_from_collection_class_items),
    path("remove_collection_class_column_data", question_views.remove_collection_class_column_data),
    path("get_writing_tasks", question_views.get_writing_tasks),
    path("add_writing_task", question_views.add_writing_task),
    path("get_writing_task_by_id", question_views.get_writing_task_by_id),
    path("delete_writing_task", question_views.delete_writing_task),
    path("update_writing_task", question_views.update_writing_task),
    path("execute_writing_task", question_views.execute_writing_task),
    path("get_dataset_templates", other_views.get_dataset_templates),
    path("create_dataset_from_template", other_views.create_dataset_from_template),
    path("change_dataset", other_views.change_dataset),
    path("delete_dataset", other_views.delete_dataset),
    path("get_import_converter", other_views.get_import_converter),
    path("get_export_converter", other_views.get_export_converter),
    path("request_service_usage", question_views.request_service_usage),
    path("convert_smart_query_to_parameters", smart_search_views.convert_smart_query_to_parameters),
]
