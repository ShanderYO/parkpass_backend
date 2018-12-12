# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0008_parking_vendor'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='max_client_debt',
            field=models.DecimalField(default=100, max_digits=10, decimal_places=2),
        ),
    ]
