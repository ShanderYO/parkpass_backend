# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_auto_20180401_1025'),
        ('payments', '0005_creditcard_exp_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='account',
            field=models.ForeignKey(blank=True, to='accounts.Account', null=True),
        ),
    ]
