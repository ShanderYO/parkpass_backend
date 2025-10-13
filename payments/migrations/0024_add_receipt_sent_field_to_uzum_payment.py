# Generated manually for adding receipt_sent field to UzumBankPayment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0023_migrate_receipts_from_raw_response'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzumbankpayment',
            name='receipt_sent',
            field=models.BooleanField(default=False, help_text='Флаг отправки чека на email'),
        ),
    ]
