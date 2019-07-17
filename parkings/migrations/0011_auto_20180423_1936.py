# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0010_auto_20180410_2046'),
    ]

    operations = [
        migrations.RenameField(
            model_name='parkingsession',
            old_name='is_paused',
            new_name='is_suspended',
        ),
        migrations.AddField(
            model_name='parkingsession',
            name='suspended_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='parkingsession',
            name='state',
            field=models.IntegerField(choices=[(-1, b'Canceled'), (1, b'Started by client'), (2, b'Started by vendor'), (3, b'Started'), (2, b'Completed by client'), (4, b'Completed by vendor'), (6, b'Completed'), (0, b'Closed')]),
        ),
    ]
