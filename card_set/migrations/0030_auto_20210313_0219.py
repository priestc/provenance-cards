# Generated by Django 3.1 on 2021-03-13 02:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card_set', '0029_card_serial_base'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='card',
            options={'ordering': ('subject__name', 'subset__name')},
        ),
        migrations.AddField(
            model_name='subset',
            name='comc_link',
            field=models.TextField(default=''),
        ),
    ]