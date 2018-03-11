# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0004_auto_20180218_1136'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, editable=False)),
                ('secret', models.CharField(unique=True, max_length=255, editable=False)),
            ],
            options={
                'ordering': ['-id'],
                'verbose_name': 'Vendor',
                'verbose_name_plural': 'Vendors',
            },
        ),
    ]
