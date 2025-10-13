# Generated manually for adding receipt_email field to UzumBankPayment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0024_add_receipt_sent_field_to_uzum_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzumbankpayment',
            name='receipt_email',
            field=models.EmailField(blank=True, help_text='Email клиента для отправки чека', null=True),
        ),
    ]
