# Generated by Django 2.1 on 2021-03-11 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_order_terminal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='sum',
            field=models.DecimalField(decimal_places=2, max_digits=16),
        ),
    ]