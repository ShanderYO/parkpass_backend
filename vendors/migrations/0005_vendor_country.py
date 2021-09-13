# Generated by Django 2.1 on 2021-09-02 09:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20210902_0904'),
        ('vendors', '0004_vendor_sms_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.Country'),
        ),
    ]
