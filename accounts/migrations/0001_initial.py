# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('first_name', models.CharField(max_length=63, null=True, blank=True)),
                ('last_name', models.CharField(max_length=63, null=True, blank=True)),
                ('phone', models.CharField(max_length=15)),
                ('sms_code', models.CharField(max_length=6)),
                ('email', models.EmailField(max_length=254, null=True, blank=True)),
                ('created_at', models.DateField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-id'],
                'verbose_name': 'Account',
                'verbose_name_plural': 'Accounts',
            },
        ),
        migrations.CreateModel(
            name='AccountSession',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('token', models.CharField(max_length=63)),
                ('expired_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('account', models.ForeignKey(to='accounts.Account', unique=True)),
            ],
            options={
                'ordering': ['-expired_at'],
            },
        ),
    ]
