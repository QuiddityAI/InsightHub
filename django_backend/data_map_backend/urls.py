from django.urls import path
from . import views

urlpatterns=[
    path("organizations", views.get_organizations, name="get-organizations"),
]
