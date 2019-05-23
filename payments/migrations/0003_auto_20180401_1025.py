# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0007_auto_20180401_1025'),
        ('accounts', '0005_auto_20180401_1025'),
        ('payments', '0002_tinkoffpayment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('sum', models.DecimalField(max_digits=7, decimal_places=2)),
                ('payment_attempts', models.PositiveSmallIntegerField(default=1)),
                ('paid', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(to='accounts.Account')),
                ('session', models.ForeignKey(blank=True, to='parkings.ParkingSession', null=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Order',
                'verbose_name_plural': 'Orders',
            },
        ),
        migrations.RemoveField(
            model_name='creditcard',
            name='number',
        ),
        migrations.RemoveField(
            model_name='tinkoffpayment',
            name='card_id',
        ),
        migrations.RemoveField(
            model_name='tinkoffpayment',
            name='pan',
        ),
        migrations.RemoveField(
            model_name='tinkoffpayment',
            name='rebill_id',
        ),
        migrations.AddField(
            model_name='creditcard',
            name='pan',
            field=models.CharField(max_length=31, blank=True),
        ),
        migrations.AddField(
            model_name='creditcard',
            name='rebill_id',
            field=models.BigIntegerField(unique=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='creditcard',
            name='id',
            field=models.IntegerField(serialize=False, primary_key=True),
        ),
        migrations.AlterField(
            model_name='tinkoffpayment',
            name='status',
            field=models.SmallIntegerField(default=0, choices=[(0, b'Init'), (1, b'New'), (2, b'Cancel'), (3, b'Form showed'), (4, b'Rejected'), (5, b'Auth fail'), (6, b'Authorized'), (7, b'Confirmed'), (9, b'Refunded'), (10, b'Partial_refunded')]),
        ),
        migrations.AddField(
            model_name='tinkoffpayment',
            name='order',
            field=models.ForeignKey(blank=True, to='payments.Order', null=True),
        ),
    ]
