# Generated manually for migrating receipts from raw_response to receipts field

from django.db import migrations


def migrate_receipts_from_raw_response(apps, schema_editor):
    """
    Переносим чеки из raw_response в отдельное поле receipts
    """
    UzumBankPayment = apps.get_model('payments', 'UzumBankPayment')
    
    for payment in UzumBankPayment.objects.filter(raw_response__isnull=False):
        if payment.raw_response and 'receipts' in payment.raw_response:
            receipts = payment.raw_response.get('receipts', [])
            if receipts:
                payment.receipts = receipts
                # Удаляем receipts из raw_response
                if 'receipts' in payment.raw_response:
                    del payment.raw_response['receipts']
                payment.save(update_fields=['receipts', 'raw_response'])


def reverse_migrate_receipts_to_raw_response(apps, schema_editor):
    """
    Обратная миграция: переносим чеки обратно в raw_response
    """
    UzumBankPayment = apps.get_model('payments', 'UzumBankPayment')
    
    for payment in UzumBankPayment.objects.filter(receipts__isnull=False):
        if payment.receipts:
            if not payment.raw_response:
                payment.raw_response = {}
            payment.raw_response['receipts'] = payment.receipts
            payment.receipts = None
            payment.save(update_fields=['receipts', 'raw_response'])


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0022_add_receipts_field_to_uzum_payment'),
    ]

    operations = [
        migrations.RunPython(
            migrate_receipts_from_raw_response,
            reverse_migrate_receipts_to_raw_response,
        ),
    ]
