# Generated by Django 2.2 on 2021-12-16 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0032_auto_20211122_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='developer',
            name='api_key',
            field=models.CharField(default='146fa72c494735a59e3650e029749f1ade3e66f3cc48f6ff', max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='developer',
            name='developer_id',
            field=models.CharField(default='46dab6c2-5e73-11ec-931d-acde48001122', max_length=128, unique=True),
        ),
    ]
