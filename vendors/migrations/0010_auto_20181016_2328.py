# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-10-16 23:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0009_delete_issue'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='actual_address',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='bik',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='checking_account',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='checking_kpp',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='inn',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='kpp',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='legal_address',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name='vendor',
            name='org_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
