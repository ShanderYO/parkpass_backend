from django.db import migrations

def migrate_verification_to_canceled(apps, schema_editor):
    ParkingSession = apps.get_model('parkings', 'ParkingSession')
    # Устанавливаем статус STATE_CANCELED и записываем сообщение в поле error для всех записей со статусом STATE_VERIFICATION_REQUIRED
    ParkingSession.objects.filter(state=21).update(state=-1, error="Verification required")

class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0050_parkingsession_error'),
    ]

    operations = [
        migrations.RunPython(migrate_verification_to_canceled),
    ]
