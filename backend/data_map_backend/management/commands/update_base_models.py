import json
import logging
import os

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.python import Deserializer
from django.utils.dateparse import parse_datetime

from data_map_backend.models import (
    DatasetSchema,
    EmbeddingSpace,
    ExportConverter,
    Generator,
    ImportConverter,
    Organization,
    User,
)
from data_map_backend.utils import DotDict


class Command(BaseCommand):
    help = "Loads and updates base models from stored definitions"

    def __init__(self):
        self.base_path = "./data_map_backend/base_model_definitions/"

    def add_arguments(self, parser):
        # parser.add_argument("poll_ids", nargs="+", type=int)
        pass

    def handle(self, *args, **options):
        self.load_model(EmbeddingSpace, "embedding_spaces")
        self.load_model(Generator, "generators")
        self.load_model(ImportConverter, "import_converters")
        self.load_model(ExportConverter, "export_converters")
        self.load_dataset_schemas()
        self.create_default_user()
        self.create_default_organization()

    def load_model(self, model_class, sub_path):
        logging.warning(f"--- Loading model '{model_class.__name__}'")
        path = self.base_path + sub_path
        definitions = []
        for file in os.listdir(path):
            if file.endswith(".json"):
                with open(path + "/" + file, "r") as f:
                    data = json.load(f)[0]
                    definitions.append(DotDict(data))

        for definition in definitions:
            if model_class.objects.filter(pk=definition.pk).exists():
                obj = model_class.objects.get(pk=definition.pk)
                definition_changed_at = parse_datetime(definition.fields.changed_at)
                assert definition_changed_at is not None
                if obj.changed_at < definition_changed_at:
                    # object needs to be updated
                    logging.warning(f"[Updated] Object '{obj}' is being updated")
                    obj = Deserializer([definition], ignorenonexistent=True).__next__()
                    obj.save()
                else:
                    logging.warning(f"[Up-to-date] Object '{obj}' is already up to date")
            else:
                logging.warning(f"[Created] Object '{definition.pk}' does not exist yet and is being created")
                obj = Deserializer([definition], ignorenonexistent=True).__next__()
                obj.save()

    def load_dataset_schemas(self):
        logging.warning(f"--- Loading dataset schemas")
        path = self.base_path + "dataset_schemas"
        definitions: list[DotDict] = []
        for file in os.listdir(path):
            if file.endswith(".json"):
                with open(path + "/" + file, "r") as f:
                    data = json.load(f)
                    definitions.append(DotDict(data))

        for definition in definitions:
            needs_update = False
            if DatasetSchema.objects.filter(pk=definition.identifier).exists():
                obj = DatasetSchema.objects.get(pk=definition.identifier)
                definition_changed_at = parse_datetime(definition.changed_at)
                assert definition_changed_at is not None
                if obj.changed_at < definition_changed_at:
                    needs_update = True
                elif len(obj.object_fields.all()) != len(definition.object_fields):
                    needs_update = True
                elif any([field["changed_at"] is not None and obj.object_fields.get(schema=obj, identifier=field["identifier"]).changed_at < parse_datetime(field["changed_at"]) for field in definition.object_fields]):  # type: ignore
                    needs_update = True
                if needs_update:
                    logging.warning(f"[Updated] Object '{obj}' is being updated")
                    # schema itself is overwritten, but fields need to be deleted and recreated:
                    obj.object_fields.all().delete()
                else:
                    logging.warning(f"[Up-to-date] Object '{obj}' is already up to date")
            else:
                logging.warning(f"[Created] Object '{definition.identifier}' does not exist yet and is being created")
                needs_update = True
            if needs_update:
                fields = {
                    item[0]: item[1]
                    for item in definition.items()
                    if item[0] not in ["applicable_import_converters", "applicable_export_converters", "object_fields"]
                }
                obj = DatasetSchema(**fields)
                obj.save()
                obj.applicable_import_converters.set(definition.applicable_import_converters)
                obj.applicable_export_converters.set(definition.applicable_export_converters)
                for field in definition.object_fields:
                    try:
                        field["generator"] = (
                            Generator.objects.get(pk=field["generator"]) if field["generator"] is not None else None
                        )
                    except Generator.DoesNotExist as e:
                        logging.error(f"Generator with pk {field['generator']} does not exist")
                        raise e
                    try:
                        field["embedding_space"] = (
                            EmbeddingSpace.objects.get(pk=field["embedding_space"])
                            if field["embedding_space"] is not None
                            else None
                        )
                    except EmbeddingSpace.DoesNotExist as e:
                        logging.error(f"EmbeddingSpace with pk {field['embedding_space']} does not exist")
                        raise e
                    obj.object_fields.create(**field)
                obj.save()

    def create_default_user(self):
        if User.objects.all().count() > 0:
            logging.warning(f"--- A user already exists, skipping creating a default one")
            return
        logging.warning(f"--- Creating default user")
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        if not username or not email or not password:
            logging.error(
                f"--- DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD must be set"
            )
            return
        try:
            User.objects.create_superuser(username, email, password)
        except Exception as e:
            logging.error(f"--- Error creating superuser: {e}")
        logging.warning(f"--- Default user {username}, e-mail {email} created")

    def create_default_organization(self):
        if Organization.objects.all().count() > 0:
            logging.warning(f"--- An organization already exists, skipping creating a default one")
            return
        logging.warning(f"--- Creating default organization")

        default_schemas_names = [
            "scientific_articles",
            "filesystem_file_german",
            "filesystem_file_english",
            "generic_data_non-english",
        ]
        default_schemas = DatasetSchema.objects.filter(name__in=default_schemas_names)
        try:
            org = Organization(name="Quiddity", is_public=True)
            org.save()
            org.schemas_for_user_created_datasets.set(default_schemas)
            org.save()
        except Exception as e:
            logging.error(f"--- Error creating organization: {e}")
        logging.warning(f"--- Default organization 'Quiddity' created")
