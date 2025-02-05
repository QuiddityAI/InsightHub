# Generated by Django 5.0.6 on 2025-01-16 18:37

from django.db import migrations, models
from django.db.models import Q


def prepare_search_rework_by_converting_results(apps, schema_editor):
    CollectionItem = apps.get_model("data_map_backend", "CollectionItem")
    candidates = CollectionItem.objects.filter(Q(relevance__gte=0) & Q(relevance__lte=1))
    candidates.update(relevance=2)
    irrelevant_candidates = CollectionItem.objects.filter(Q(relevance=-1))
    irrelevant_candidates.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0051_user_preferences"),
    ]

    operations = [
        migrations.RunPython(prepare_search_rework_by_converting_results, reverse_code=migrations.RunPython.noop),
    ]
