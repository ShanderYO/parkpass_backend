# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Parking',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=63, null=True, blank=True)),
                ('description', models.TextField()),
                ('address', models.CharField(max_length=63, null=True, blank=True)),
                ('latitude', models.DecimalField(max_digits=10, decimal_places=8)),
                ('longitude', models.DecimalField(max_digits=11, decimal_places=8)),
                ('enabled', models.BooleanField(default=True)),
                ('free_places', models.IntegerField()),
                ('created_at', models.DateField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-id'],
                'verbose_name': 'Parking',
                'verbose_name_plural': 'Parkings',
            },
        ),
    ]
