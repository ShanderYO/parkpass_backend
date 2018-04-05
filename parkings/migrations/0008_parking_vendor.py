# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0007_auto_20180401_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='vendor',
            field=models.ForeignKey(blank=True, to='parkings.Vendor', null=True),
        ),
    ]
