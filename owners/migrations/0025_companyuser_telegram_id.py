# Generated by Django 2.2 on 2022-06-10 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0024_auto_20220516_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyuser',
            name='telegram_id',
            field=models.CharField(blank=True, max_length=63, null=True),
        ),
    ]
