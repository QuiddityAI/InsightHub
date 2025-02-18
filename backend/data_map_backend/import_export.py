from import_export import resources

from data_map_backend.models import User


class UserResource(resources.ModelResource):
    class Meta:
        model = User
