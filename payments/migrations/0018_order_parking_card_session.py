# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2019-05-02 20:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0027_parkingcard_rpsparkingcardsession'),
        ('payments', '0017_order_client_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='parking_card_session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rps_vendor.RpsParkingCardSession'),
        ),
    ]
