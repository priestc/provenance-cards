# Generated by Django 3.1.7 on 2021-03-26 04:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card_set', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='multi_base_population',
            field=models.FloatField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name='subset',
            name='card_number_critical',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='subset',
            name='statistical_serial_base',
            field=models.FloatField(blank=True, default=0),
        ),
    ]
