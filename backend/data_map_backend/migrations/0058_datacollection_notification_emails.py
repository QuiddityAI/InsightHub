# Generated by Django 5.0.6 on 2025-01-26 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0057_alter_writingtask_parameters"),
    ]

    operations = [
        migrations.AddField(
            model_name="datacollection",
            name="notification_emails",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Email addresses for notifications about new items, comma separated",
                verbose_name="Notification Emails",
            ),
        ),
    ]
