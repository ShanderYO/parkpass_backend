# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TinkoffPayment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_id', models.BigIntegerField(unique=True, null=True, blank=True)),
                ('status', models.SmallIntegerField(default=0, choices=[(0, b'Init'), (1, b'New'), (2, b'Cancel'), (3, b'Form showed'), (4, b'Rejected'), (5, b'Auth fail'), (6, b'Authorized')])),
                ('rebill_id', models.BigIntegerField(unique=True, null=True, blank=True)),
                ('card_id', models.BigIntegerField(unique=True, null=True, blank=True)),
                ('pan', models.CharField(max_length=31, null=True, blank=True)),
                ('error_code', models.IntegerField(default=-1)),
                ('error_message', models.CharField(max_length=127, null=True, blank=True)),
                ('error_description', models.TextField(max_length=511, null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Tinkoff Payment',
                'verbose_name_plural': 'Tinkoff Payments',
            },
        ),
    ]
