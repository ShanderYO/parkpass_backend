# Generated by Django 2.2 on 2022-05-09 11:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0028_parkingvaletsession_duration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='parkingvaletsession',
            name='parking_card',
        ),
    ]
