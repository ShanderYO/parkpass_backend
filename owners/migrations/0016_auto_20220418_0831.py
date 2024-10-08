# Generated by Django 2.2 on 2022-04-18 08:31

import django.contrib.auth.password_validation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0015_companyuser_password'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companyuser',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name='companyuser',
            name='password',
            field=models.CharField(max_length=255, validators=[django.contrib.auth.password_validation.validate_password]),
        ),
    ]
