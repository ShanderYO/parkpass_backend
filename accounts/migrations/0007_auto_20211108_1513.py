# Generated by Django 2.1 on 2021-11-08 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_auto_20211108_1512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='email_fiskal_notification_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
