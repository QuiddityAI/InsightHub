# created manually

import data_map_backend.models
import django.db.models.deletion
import django.utils.timezone
from django.db import IntegrityError, migrations, models

from data_map_backend.models import FieldType


def combine_names(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    DataCollection = apps.get_model("data_map_backend", "DataCollection")
    CollectionItem = apps.get_model("data_map_backend", "CollectionItem")
    CollectionColumn = apps.get_model("data_map_backend", "CollectionColumn")
    for collection in DataCollection.objects.all():
        for question in (collection.extraction_questions or []):
            column_identifier = question["name"].replace(" ", "_").lower()
            if CollectionColumn.objects.filter(collection=collection, identifier=column_identifier).exists():
                continue
            CollectionColumn.objects.create(
                collection=collection,
                name=question["name"],
                identifier=question["name"].replace(" ", "_").lower(),
                field_type=FieldType.TEXT,
                expression=question["prompt"],
                source_fields=question["source_fields"],
                module=question.get("module"),
                parameters={},
            )

    for item in CollectionItem.objects.all():
        new_data = {}
        for column_name, extraction_answer in item.column_data.items():
            if isinstance(extraction_answer, dict):
                # is already in new format
                new_data[column_name] = extraction_answer
            column_identifier = column_name.replace(" ", "_").lower()
            new_data[column_identifier] = {
                'value': extraction_answer,
                'changed_at': None,
            }
        item.column_data = new_data
        item.save()



class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0016_remove_collectionitem_extraction_answers_and_more'),
    ]

    operations = [
        migrations.RunPython(combine_names),
    ]
