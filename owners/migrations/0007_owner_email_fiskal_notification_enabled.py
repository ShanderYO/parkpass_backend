# Generated by Django 2.1 on 2021-11-08 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0006_owner_country'),
    ]

    operations = [
        migrations.AddField(
            model_name='owner',
            name='email_fiskal_notification_enabled',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
