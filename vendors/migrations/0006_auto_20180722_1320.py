# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-07-22 13:20
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vendors', '0005_auto_20180722_1238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='phone',
            field=models.CharField(default=django.utils.timezone.now, max_length=13),
            preserve_default=False,
        ),
    ]
