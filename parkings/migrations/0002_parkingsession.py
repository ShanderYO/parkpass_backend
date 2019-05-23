# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20180218_0956'),
        ('parkings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParkingSession',
            fields=[
                ('id', models.AutoField(unique=True, serialize=False, primary_key=True)),
                ('session_id', models.CharField(max_length=64)),
                ('is_paused', models.BooleanField(default=False)),
                ('debt', models.DecimalField(default=0, max_digits=7, decimal_places=2)),
                ('state', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('client', models.ForeignKey(to='accounts.Account')),
                ('parking', models.ForeignKey(to='parkings.Parking')),
            ],
        ),
    ]
