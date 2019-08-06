# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_remove_order_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditcard',
            name='exp_date',
            field=models.CharField(max_length=61, blank=True),
        ),
    ]
