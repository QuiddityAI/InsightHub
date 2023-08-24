"""
URL configuration for project_base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def redirect_to_admin(request):
    response = redirect('admin/')
    return response


urlpatterns = [
    path('', redirect_to_admin),  # we only use the admin interface for now
    path('admin/', admin.site.urls),
    path("data_map/", include('data_map_backend.urls')),
    path('api-auth/', include('rest_framework.urls'))
]
