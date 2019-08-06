# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20180120_1626'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountParkingSession',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('linked_session_id', models.CharField(max_length=128)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaidDebt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('paid_debt', models.DecimalField(max_digits=7, decimal_places=2)),
                ('linked_session_id', models.CharField(max_length=128)),
                ('is_completed', models.BooleanField(default=False)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('account', models.ForeignKey(to='accounts.Account')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='account',
            name='parking_session',
            field=models.ForeignKey(blank=True, to='accounts.AccountParkingSession', null=True),
        ),
    ]
