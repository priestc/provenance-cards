# Generated by Django 3.1 on 2021-01-28 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card_set', '0009_auto_20210126_0851'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='youtube_identifier',
            field=models.TextField(unique=True),
        ),
    ]