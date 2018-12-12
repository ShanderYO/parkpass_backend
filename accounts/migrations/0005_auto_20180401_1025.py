# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20180218_1504'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paiddebt',
            name='account',
        ),
        migrations.RemoveField(
            model_name='paiddebt',
            name='parking',
        ),
        migrations.AlterField(
            model_name='accountsession',
            name='account',
            field=models.OneToOneField(to='accounts.Account'),
        ),
        migrations.DeleteModel(
            name='PaidDebt',
        ),
    ]
