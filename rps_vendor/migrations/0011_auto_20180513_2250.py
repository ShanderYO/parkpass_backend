# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-05-13 22:50
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0010_auto_20180513_2249'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rpsparking',
            name='last_request_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 5, 13, 22, 50, 36, 47495)),
        ),
    ]
