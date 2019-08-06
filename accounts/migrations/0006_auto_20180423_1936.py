# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_auto_20180401_1025'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='parking_session',
        ),
        migrations.DeleteModel(
            name='AccountParkingSession',
        ),
    ]
