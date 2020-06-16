# Generated by Django 2.1 on 2020-06-14 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0004_auto_20200517_1202'),
    ]

    operations = [
        migrations.AddField(
            model_name='rpsparking',
            name='request_get_subscriptions_list_url',
            field=models.URLField(default='https://parkpass.ru/api/v1/parking/rps/mock/subscriptions/'),
        ),
        migrations.AddField(
            model_name='rpsparking',
            name='request_subscription_pay_url',
            field=models.URLField(default='https://parkpass.ru/api/v1/parking/rps/mock/subscription/pay/'),
        ),
    ]
