# Generated by Django 3.1 on 2021-03-15 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card_set', '0030_auto_20210313_0219'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subset',
            name='comc_link',
        ),
        migrations.AddField(
            model_name='subset',
            name='comc_color',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='subset',
            name='comc_name',
            field=models.TextField(blank=True, default=''),
        ),
    ]
