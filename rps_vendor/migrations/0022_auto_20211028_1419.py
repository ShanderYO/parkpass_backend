# Generated by Django 2.1 on 2021-10-28 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0021_auto_20211027_1236'),
    ]

    operations = [
        migrations.AlterField(
            model_name='developer',
            name='api_key',
            field=models.CharField(default='42506d001f120281b17fad0b2dc3c47cf6051203027ae47d', max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='developer',
            name='developer_id',
            field=models.CharField(default='1f589b90-37fa-11ec-a146-acde48001122', max_length=128, unique=True),
        ),
    ]
