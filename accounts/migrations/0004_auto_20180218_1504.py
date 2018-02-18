# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0004_auto_20180218_1136'),
        ('accounts', '0003_auto_20180218_0956'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountparkingsession',
            name='canceled_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='accountparkingsession',
            name='parking_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='paiddebt',
            name='parking',
            field=models.ForeignKey(blank=True, to='parkings.Parking', null=True),
        ),
        migrations.AlterField(
            model_name='accountparkingsession',
            name='completed_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
