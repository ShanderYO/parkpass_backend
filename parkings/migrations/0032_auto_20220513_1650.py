# Generated by Django 2.2 on 2022-05-13 16:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0031_auto_20220509_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='parking_card',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='rps_vendor.ParkingCard'),
        ),
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='parking_space_number',
            field=models.CharField(max_length=20, null=True),
        ),
    ]
