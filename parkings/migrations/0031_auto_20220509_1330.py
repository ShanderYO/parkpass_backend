# Generated by Django 2.2 on 2022-05-09 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0030_parkingvaletsession_parking_card'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='started_at',
            field=models.DateTimeField(),
        ),
    ]
