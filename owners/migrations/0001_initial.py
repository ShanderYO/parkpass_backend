# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2020-01-10 19:56
from __future__ import unicode_literals

import accounts.validators
import base.validators
from django.db import migrations, models
import django.db.models.deletion
import owners.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('inn', models.CharField(blank=True, max_length=15, null=True, validators=(owners.validators.validate_inn,))),
                ('kpp', models.CharField(blank=True, max_length=15, null=True, validators=(owners.validators.validate_kpp,))),
                ('bic', models.CharField(blank=True, max_length=20, null=True)),
                ('legal_address', models.CharField(max_length=512)),
                ('actual_address', models.CharField(max_length=512)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=15, null=True, validators=(base.validators.validate_phone_number,))),
                ('use_profile_contacts', models.BooleanField(default=False)),
                ('bank', models.CharField(blank=True, max_length=256, null=True)),
                ('account', models.CharField(blank=True, max_length=64, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('first_name', models.CharField(blank=True, max_length=63, null=True)),
                ('last_name', models.CharField(blank=True, max_length=63, null=True)),
                ('phone', models.CharField(max_length=15)),
                ('sms_code', models.CharField(blank=True, max_length=6, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('password', models.CharField(default=b'stub', max_length=255)),
                ('avatar', models.CharField(blank=True, max_length=64, null=True)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'ordering': ['-id'],
                'abstract': False,
                'verbose_name': 'Account',
                'verbose_name_plural': 'Accounts',
            },
        ),
        migrations.CreateModel(
            name='OwnerApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.PositiveSmallIntegerField(choices=[(1, 'Connect parking'), (2, 'Software update'), (3, 'Install readers')])),
                ('contact_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('contact_phone', models.CharField(blank=True, max_length=13, null=True)),
                ('description', models.CharField(max_length=1000)),
                ('status', models.PositiveSmallIntegerField(choices=[(1, 'New'), (2, 'Processing'), (3, 'Processed'), (4, 'Cancelled')], default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='owners.Company')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='owners.Owner')),
            ],
        ),
        migrations.CreateModel(
            name='OwnerIssue',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('type', models.PositiveSmallIntegerField(choices=[(1, b'Type owner'), (2, b'Type vendor')])),
                ('name', models.CharField(max_length=255, validators=(accounts.validators.validate_name,))),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(max_length=13, validators=(base.validators.validate_phone_number,))),
                ('comment', models.CharField(blank=True, max_length=1023, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OwnerSession',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('token', models.CharField(max_length=63)),
                ('expired_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('owner', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='owners.Owner')),
            ],
            options={
                'ordering': ['-expired_at'],
                'abstract': False,
            },
        ),
    ]
