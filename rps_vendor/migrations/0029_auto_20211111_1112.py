# Generated by Django 2.1 on 2021-11-11 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0028_auto_20211110_1600'),
    ]

    operations = [
        migrations.AlterField(
            model_name='developer',
            name='api_key',
            field=models.CharField(default='51c2dcb29f6bffdd3617796fb548a2733ca81f0201031b8c', max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='developer',
            name='developer_id',
            field=models.CharField(default='53159488-42e0-11ec-bcfa-acde48001122', max_length=128, unique=True),
        ),
    ]
