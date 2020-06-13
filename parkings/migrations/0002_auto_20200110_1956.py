# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2020-01-10 19:56
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vendors', '0001_initial'),
        ('parkings', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendors.Vendor'),
        ),
        migrations.AddField(
            model_name='complainsession',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.Account'),
        ),
        migrations.AddField(
            model_name='complainsession',
            name='session',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parkings.ParkingSession'),
        ),
        migrations.AlterUniqueTogether(
            name='parkingsession',
            unique_together=set([('session_id', 'parking')]),
        ),
    ]
