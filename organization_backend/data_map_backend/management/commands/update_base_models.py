import os
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.core.serializers.python import Deserializer

from data_map_backend.models import EmbeddingSpace, Generator
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
