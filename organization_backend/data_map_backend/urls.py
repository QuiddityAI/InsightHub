from django.urls import path
from . import views

urlpatterns=[
    path("object_schema", views.get_object_schema),
    path("available_schemas", views.get_available_schemas),
    path("add_search_history_item", views.add_search_history_item),
    path("get_search_history", views.get_search_history),
    path("add_item_collection", views.add_item_collection),
    path("add_stored_map", views.add_stored_map),
]
