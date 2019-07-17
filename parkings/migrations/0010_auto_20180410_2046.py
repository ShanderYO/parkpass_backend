# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0009_parking_max_client_debt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingsession',
            name='session_id',
            field=models.CharField(max_length=128),
        ),
    ]
