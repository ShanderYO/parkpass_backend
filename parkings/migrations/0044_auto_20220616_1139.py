# Generated by Django 2.2 on 2022-06-16 11:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0043_parkingvaletsession_vcid'),
    ]

    operations = [
        migrations.RenameField(
            model_name='parkingvaletsession',
            old_name='vcid',
            new_name='pcid',
        ),
    ]
