# Generated by Django 2.1 on 2021-08-28 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0015_auto_20210827_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='developer',
            name='api_key',
            field=models.CharField(default='be95fe5b5fde9c8586be8685574d3a6418fd9c9e9657e827', max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='developer',
            name='developer_id',
            field=models.CharField(default='472885d0-07e5-11ec-b1df-acde48001122', max_length=128, unique=True),
        ),
    ]
