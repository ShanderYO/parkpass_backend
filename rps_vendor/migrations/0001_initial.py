# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0011_auto_20180423_1936'),
    ]

    operations = [
        migrations.CreateModel(
            name='RpsParking',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('request_update_url', models.URLField(null=True, blank=True)),
                ('last_request', models.DateTimeField(default=datetime.datetime(2018, 4, 25, 22, 12, 30, 981655))),
                ('last_response_code', models.IntegerField(default=0)),
                ('last_response_body', models.TextField(null=True, blank=True)),
                ('parking', models.ForeignKey(to='parkings.Parking')),
            ],
            options={
                'ordering': ['-id'],
                'verbose_name': 'RpsParking',
                'verbose_name_plural': 'RpsParking',
            },
        ),
    ]
