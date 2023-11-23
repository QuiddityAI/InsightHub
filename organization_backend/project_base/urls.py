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
from django.urls import path, include, re_path
from django.shortcuts import redirect

from django.contrib.auth import views as auth_views
import data_map_backend


def redirect_to_admin(request):
    response = redirect('admin/')
    return response


urlpatterns = [
    path('org/', include('social_django.urls', namespace='social')),
    # path('', redirect_to_admin),  # we only use the admin interface for now
    path('org/admin/', admin.site.urls),
    path("org/data_map/", include('data_map_backend.urls')),
    path('org/api-auth/', include('rest_framework.urls')),
    re_path(r'^org/auth/', include('drf_social_oauth2.urls', namespace='drf')),
    path('org/', data_map_backend.views.HomeView.as_view(), name='home'),

    # Login and Logout
    path('org/login/', auth_views.LoginView.as_view(), name='login'),
    path('org/logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # OAuth toolkit
    path("org/o/", include('oauth2_provider.urls', namespace='oauth2_provider')),
]
