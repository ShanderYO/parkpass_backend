# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0002_auto_20180425_2216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rpsparking',
            name='last_request',
            field=models.DateTimeField(default=datetime.datetime(2018, 5, 9, 10, 56, 13, 717973)),
        ),
    ]
