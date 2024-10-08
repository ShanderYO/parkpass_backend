# Generated by Django 2.1 on 2020-06-14 16:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0004_parking_rps_subscriptions_available'),
        ('accounts', '0002_auto_20200614_1642'),
        ('vendors', '0002_vendornotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='fetch_extern_user_data_url',
            field=models.URLField(max_length=1024, null=True),
        ),
    ]
