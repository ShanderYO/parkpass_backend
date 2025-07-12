from django.db import migrations

def update_states_to_exit_allowed(apps, schema_editor):
    ParkingSession = apps.get_model('parkings', 'ParkingSession')
    
    # Обновление статусов
    ParkingSession.objects.filter(state__in=[6, 7, 10, 11]).update(state=12)  # 12 - это значение для EXIT_ALLOWED

class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0047_auto_20241110_0704'),
    ]

    operations = [
        migrations.RunPython(update_states_to_exit_allowed),
    ]
