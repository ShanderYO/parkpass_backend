# Generated by Django 2.1 on 2021-08-27 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0011_parkingsession_canceled_sum'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkingsession',
            name='paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
