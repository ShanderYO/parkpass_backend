# Generated by Django 2.1 on 2021-03-16 16:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0012_auto_20210316_1548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homebankfiskalnotification',
            name='check_number',
            field=models.BigIntegerField(),
        ),
    ]
