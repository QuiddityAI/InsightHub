from django.urls import path
from . import views

urlpatterns=[
    path("health", views.get_health),
    path("get_current_user", views.get_current_user),
    path("available_organizations", views.get_available_organizations),
    path("dataset", views.get_dataset),
    path("available_datasets", views.get_available_datasets),
    path("add_search_history_item", views.add_search_history_item),
    path("get_search_history", views.get_search_history),
    path("add_collection", views.add_collection),
    path("add_collection_class", views.add_collection_class),
    path("delete_collection_class", views.delete_collection_class),
    path("get_collections", views.get_collections),
    path("get_collection", views.get_collection),
    path("get_trained_classifier", views.get_trained_classifier),
    path("set_trained_classifier", views.set_trained_classifier),
    path("get_collection_items", views.get_collection_items),
    path("delete_collection", views.delete_collection),
    path("add_item_to_collection", views.add_item_to_collection),
    path("remove_collection_item", views.remove_collection_item),
    path("remove_collection_item_by_value", views.remove_collection_item_by_value),
    path("add_stored_map", views.add_stored_map),
    path("get_stored_maps", views.get_stored_maps),
    path("stored_map_data", views.get_stored_map_data),
    path("delete_stored_map", views.delete_stored_map),
    path("get_generators", views.get_generators),
]
