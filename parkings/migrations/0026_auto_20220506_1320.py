# Generated by Django 2.2 on 2022-05-06 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0025_parkingvaletsessionrequest_company'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='started_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='parkingvaletsessionrequest',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='parkingvaletsessionrequest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
