# Generated by Django 2.2 on 2022-06-07 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0036_auto_20220524_1324'),
    ]

    operations = [
        migrations.AddField(
            model_name='parking',
            name='valet_email',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
