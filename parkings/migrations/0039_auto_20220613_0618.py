# Generated by Django 2.2 on 2022-06-13 06:18

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0038_parking_valet_telegram_secret_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parking',
            name='valet_telegram_secret_key',
            field=models.CharField(blank=True, default=uuid.uuid4, max_length=128, null=True),
        ),
    ]
