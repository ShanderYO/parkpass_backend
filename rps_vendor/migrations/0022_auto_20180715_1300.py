# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-07-15 13:00
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0021_auto_20180715_1227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rpsparking',
            name='last_request_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 7, 15, 13, 0, 8, 737406)),
        ),
    ]
