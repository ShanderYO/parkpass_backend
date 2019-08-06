# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20180120_1626'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditCard',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('number', models.CharField(max_length=30, verbose_name=b'Number', blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('account', models.ForeignKey(related_name='credit_cards', to='accounts.Account')),
            ],
            options={
                'ordering': ['-id'],
                'verbose_name': 'CreditCard',
                'verbose_name_plural': 'CreditCards',
            },
        ),
    ]
