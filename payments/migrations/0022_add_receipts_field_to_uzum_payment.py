# Generated manually for adding receipts field to UzumBankPayment

from django.db import migrations, models
import django.contrib.postgres.fields.jsonb


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0021_auto_20250728_1843'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzumbankpayment',
            name='receipts',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='Чеки об оплате от Uzum Bank', null=True),
        ),
    ]
