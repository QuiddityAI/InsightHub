from django.urls import path
from . import views

urlpatterns=[
    path("object_schema", views.get_object_schema, name="get-object-schema"),
]
