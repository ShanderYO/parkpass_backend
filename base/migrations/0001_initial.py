# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-06-09 13:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Terminal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('terminal_key', models.CharField(max_length=255)),
                ('password', models.CharField(max_length=255)),
                ('is_selected', models.BooleanField(default=False)),
            ],
        ),
    ]
