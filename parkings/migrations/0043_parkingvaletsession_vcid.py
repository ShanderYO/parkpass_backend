# Generated by Django 2.2 on 2022-06-16 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0042_parkingvaletsessionrequest_notificated_about_car_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkingvaletsession',
            name='vcid',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
