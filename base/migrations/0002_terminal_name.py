# Generated by Django 2.1 on 2020-06-14 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='terminal',
            name='name',
            field=models.CharField(max_length=255, null=True, unique=True),
        ),
    ]
