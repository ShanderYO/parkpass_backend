# Generated by Django 2.1 on 2021-11-11 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0013_auto_20211111_1112'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='hide_parking_coordinates',
            field=models.BooleanField(default=False, verbose_name='Скрыть парковку с карты'),
        ),
    ]
