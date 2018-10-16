# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0002_parkingsession'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingsession',
            name='completed_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='parkingsession',
            name='state',
            field=models.IntegerField(default=0, choices=[(-1, b'Canceled'), (0, b'Started'), (1, b'Updated'), (2, b'Completed')]),
        ),
        migrations.AlterField(
            model_name='parkingsession',
            name='updated_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
