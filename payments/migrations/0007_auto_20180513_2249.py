# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-05-13 22:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_order_account'),
    ]

    operations = [
        migrations.CreateModel(
            name='FiskalNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fiscal_number', models.IntegerField()),
                ('shift_number', models.IntegerField()),
                ('receipt_datetime', models.DateTimeField()),
                ('fn_number', models.CharField(max_length=20)),
                ('ecr_reg_number', models.CharField(max_length=20)),
                ('fiscal_document_number', models.IntegerField()),
                ('fiscal_document_attribute', models.IntegerField()),
                ('token', models.TextField()),
                ('ofd', models.TextField(blank=True, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('qr_code_url', models.URLField(blank=True, null=True)),
                ('receipt', models.TextField()),
                ('type', models.CharField(max_length=15)),
            ],
            options={
                'ordering': ['-receipt_datetime'],
            },
        ),
        migrations.AddField(
            model_name='tinkoffpayment',
            name='receipt_data',
            field=models.TextField(blank=True, null=True),
        ),
    ]
