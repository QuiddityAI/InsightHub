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
    path("add_classifier", views.add_classifier),
    path("add_classifier_class", views.add_classifier_class),
    path("delete_classifier_class", views.delete_classifier_class),
    path("get_classifiers", views.get_classifiers),
    path("get_classifier", views.get_classifier),
    path("get_classifier_examples", views.get_classifier_examples),
    path("delete_classifier", views.delete_classifier),
    path("add_item_to_classifier", views.add_item_to_classifier),
    path("remove_classifier_example", views.remove_classifier_example),
    path("remove_classifier_example_by_value", views.remove_classifier_example_by_value),
    path("add_stored_map", views.add_stored_map),
    path("get_stored_maps", views.get_stored_maps),
    path("stored_map_data", views.get_stored_map_data),
    path("delete_stored_map", views.delete_stored_map),
    path("get_generators", views.get_generators),
]
