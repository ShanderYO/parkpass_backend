# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-12-05 03:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailConfirmation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('code', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account_type', models.CharField(choices=[(b'User', b'account'), (b'Vendor', b'vendor'), (b'Owner', b'owner')], default=b'account', max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='NotifyIssue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=15)),
            ],
        ),
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
