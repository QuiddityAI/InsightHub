# Generated by Django 5.0.3 on 2024-03-27 19:20

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0002_collectionchat_created_by_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CollectionChat',
            new_name='Chat',
        ),
        migrations.AlterModelOptions(
            name='chat',
            options={'verbose_name': 'Chat', 'verbose_name_plural': 'Chats'},
        ),
    ]
