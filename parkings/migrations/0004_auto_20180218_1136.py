# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0003_auto_20180218_1023'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='parkingsession',
            options={'ordering': ['-id'], 'verbose_name': 'Parking Session', 'verbose_name_plural': 'Parking Sessions'},
        ),
        migrations.AlterUniqueTogether(
            name='parkingsession',
            unique_together=set([('session_id', 'parking')]),
        ),
    ]
