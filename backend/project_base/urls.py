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
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path, re_path

from columns.views import api as columns_api
from data_map_backend.views import data_backend_proxy_views, other_views
from data_map_backend.views.collection_management import (
    api as collection_management_api,
)
from filter.views import api as filter_api
from ingest.views import api as ingest_api
from map.views import api as map_api
from project_base.views import (
    change_password_from_app,
    consider_buying,
    credits_bought,
    login_from_app,
    signup_from_app,
)
from search.views import api as search_api
from workflows.views import api as workflows_api
from write.views import api as write_api


def redirect_to_admin(request):
    response = redirect("admin/")
    return response


urlpatterns = [
    path("org/", include("social_django.urls", namespace="social")),
    # path('', redirect_to_admin),  # we only use the admin interface for now
    path("org/admin/", admin.site.urls),
    path("org/data_map/", include("data_map_backend.urls")),
    path("org/api-auth/", include("rest_framework.urls")),
    re_path(r"^org/auth/", include("drf_social_oauth2.urls", namespace="drf")),
    path("org/", other_views.HomeView.as_view(), name="home"),
    path("legacy_backend/", include("legacy_backend.urls")),
    path(
        "data_backend/<path:sub_path>",
        data_backend_proxy_views.data_backend_proxy_view,
        name="data_backend_proxy_view",
    ),
    path("api/v1/ingest/", ingest_api.urls),
    path("api/v1/workflows/", workflows_api.urls),
    path("api/v1/search/", search_api.urls),
    path("api/v1/columns/", columns_api.urls),
    path("api/v1/map/", map_api.urls),
    path("api/v1/filter/", filter_api.urls),
    path("api/v1/write/", write_api.urls),
    path("api/v1/collections/", collection_management_api.urls),
    # Login and Logout
    path("org/login/", auth_views.LoginView.as_view(), name="login"),
    path("org/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("org/login_from_app/", login_from_app, name="login_from_app"),
    path("org/consider_buying/", consider_buying, name="consider_buying"),
    path("org/credits_bought/", credits_bought, name="credits_bought"),
    path("org/signup_from_app/", signup_from_app, name="signup_from_app"),
    path("org/change_password_from_app/", change_password_from_app, name="change_password_from_app"),
    # OAuth toolkit
    path("org/o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    # Django Prometheus / Grafana
    path("", include("django_prometheus.urls")),
]
