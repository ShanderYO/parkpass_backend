# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-10-16 23:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0019_auto_20180909_2011'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='tariff',
            field=models.CharField(default=b'{}', max_length=2000, verbose_name=b'Tariff object JSON'),
        ),
        migrations.AlterField(
            model_name='parking',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
