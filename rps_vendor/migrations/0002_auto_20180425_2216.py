# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rpsparking',
            name='last_request',
            field=models.DateTimeField(default=datetime.datetime(2018, 4, 25, 22, 16, 21, 560126)),
        ),
    ]
