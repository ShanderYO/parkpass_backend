# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0011_auto_20180423_1936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingsession',
            name='state',
            field=models.IntegerField(choices=[(-1, b'Canceled'), (1, b'Started_by_client'), (2, b'Started_by_vendor'), (3, b'Started'), (6, b'Completed_by_client'), (7, b'Completed_by_client_fully'), (10, b'Completed_by_vendor'), (11, b'Completed_by_vendor_fully'), (14, b'Completed'), (0, b'Closed')]),
        ),
    ]
