from django.db import migrations


def update_writing_task_model_to_new_models(apps, schema_editor):
    WritingTask = apps.get_model("data_map_backend", "WritingTask")
    for writing_task in WritingTask.objects.all():
        writing_task.module = "Google_Gemini_Flash_1_5_v1"
        writing_task.save()


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0038_generationtask"),
    ]

    operations = [
        migrations.RunPython(update_writing_task_model_to_new_models, reverse_code=migrations.RunPython.noop),
    ]
