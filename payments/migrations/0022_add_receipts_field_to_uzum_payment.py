# Generated manually for adding receipts field to UzumBankPayment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0021_auto_20250728_1843'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzumbankpayment',
            name='receipts',
            field=models.JSONField(blank=True, help_text='Чеки об оплате от Uzum Bank', null=True),
        ),
    ]
