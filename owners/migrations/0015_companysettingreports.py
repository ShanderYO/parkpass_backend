# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2019-08-23 16:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import owners.models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0031_parking_rps_subscriptions_available'),
        ('owners', '0014_auto_20190502_2012'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanySettingReports',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available', models.BooleanField(default=True)),
                ('report_emails', models.TextField(blank=True, null=True, validators=(owners.models.comma_separated_emails,))),
                ('period_in_days', models.IntegerField(default=30)),
                ('last_send_date', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='owners.Company')),
                ('parking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parkings.Parking')),
            ],
            options={
                'db_table': 'report_settings',
            },
        ),
    ]
