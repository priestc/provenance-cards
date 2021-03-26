# Generated by Django 3.1.7 on 2021-03-26 21:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('card_pull', '0002_box_completly_indexed'),
    ]

    operations = [
        migrations.AddField(
            model_name='box',
            name='indexed_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='box',
            name='indexed_on',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
    ]
