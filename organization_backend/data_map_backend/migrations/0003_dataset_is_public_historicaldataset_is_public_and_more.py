# Generated by Django 4.2.7 on 2023-11-23 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0002_generator_image_similarity_threshold_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='Is public'),
        ),
        migrations.AddField(
            model_name='historicaldataset',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='Is public'),
        ),
        migrations.AlterField(
            model_name='generator',
            name='image_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity an image query must have compared to this field to be considered relevant / similar', null=True, verbose_name='Image Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='generator',
            name='text_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity a text query must have compared to this field to be considered relevant / similar', null=True, verbose_name='Text Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='historicalgenerator',
            name='image_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity an image query must have compared to this field to be considered relevant / similar', null=True, verbose_name='Image Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='historicalgenerator',
            name='text_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity a text query must have compared to this field to be considered relevant / similar', null=True, verbose_name='Text Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='image_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity an image query must have compared to this field to be considered relevant / similar (overriding the generators value)', null=True, verbose_name='Image Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='text_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity a text query must have compared to this field to be considered relevant / similar (overriding the generators value)', null=True, verbose_name='Text Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='image_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity an image query must have compared to this field to be considered relevant / similar (overriding the generators value)', null=True, verbose_name='Image Similarity Threshold'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='text_similarity_threshold',
            field=models.FloatField(blank=True, help_text='The minimum score / similarity a text query must have compared to this field to be considered relevant / similar (overriding the generators value)', null=True, verbose_name='Text Similarity Threshold'),
        ),
    ]
