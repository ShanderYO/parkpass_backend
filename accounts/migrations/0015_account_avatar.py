# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2019-01-26 20:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_auto_20181113_2108'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='avatar',
            field=models.CharField(default=True, max_length=64, null=True),
        ),
    ]
