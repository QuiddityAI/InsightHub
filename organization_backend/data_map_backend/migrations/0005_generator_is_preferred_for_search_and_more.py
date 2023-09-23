# Generated by Django 4.2.5 on 2023-09-23 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0004_alter_embeddingspace_dimensions_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generator',
            name='is_preferred_for_search',
            field=models.BooleanField(default=False, help_text='Enabled this if this generator is optimized for short search queries', verbose_name='Is preferred for search'),
        ),
        migrations.AddField(
            model_name='historicalgenerator',
            name='is_preferred_for_search',
            field=models.BooleanField(default=False, help_text='Enabled this if this generator is optimized for short search queries', verbose_name='Is preferred for search'),
        ),
    ]
