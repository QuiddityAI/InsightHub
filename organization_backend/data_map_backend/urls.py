from django.urls import path
from . import views

urlpatterns=[
    path("health", views.get_health),
    path("dataset", views.get_dataset),
    path("available_datasets", views.get_available_datasets),
    path("add_search_history_item", views.add_search_history_item),
    path("get_search_history", views.get_search_history),
    path("add_item_collection", views.add_item_collection),
    path("get_item_collections", views.get_item_collections),
    path("get_item_collection", views.get_item_collection),
    path("delete_item_collection", views.delete_item_collection),
    path("add_item_to_collection", views.add_item_to_collection),
    path("remove_item_from_collection", views.remove_item_from_collection),
    path("add_stored_map", views.add_stored_map),
    path("get_stored_maps", views.get_stored_maps),
    path("stored_map_data", views.get_stored_map_data),
    path("delete_stored_map", views.delete_stored_map),
    path("get_generators", views.get_generators),
]
