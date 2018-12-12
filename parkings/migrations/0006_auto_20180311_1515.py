# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0005_vendor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='name',
            field=models.CharField(unique=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='secret',
            field=models.CharField(unique=True, max_length=255),
        ),
    ]
