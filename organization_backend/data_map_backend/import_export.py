from import_export import resources
from django.contrib.auth.models import User


class UserResource(resources.ModelResource):
    class Meta:
        model = User
