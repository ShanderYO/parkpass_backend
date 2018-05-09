# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0003_auto_20180509_1056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rpsparking',
            name='last_request',
            field=models.DateTimeField(default=datetime.datetime(2018, 5, 9, 10, 58, 53, 540361)),
        ),
    ]
