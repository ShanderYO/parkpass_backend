# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2019-01-15 09:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0010_auto_20190112_0906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ownerapplication',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
