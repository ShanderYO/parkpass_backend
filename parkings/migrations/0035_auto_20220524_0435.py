# Generated by Django 2.2 on 2022-05-24 04:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0034_auto_20220518_1334'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkingvaletsession',
            name='parking_place',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='parkingvaletsession',
            name='state',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Принял автомобиль'), (2, 'Парковка автомобиля'), (3, 'Автомобиль припаркован'), (4, 'Запрошена подача автомобиля'), (5, 'В процессе подачи'), (6, 'Назначен ответственный'), (7, 'Машина ожидает'), (8, 'Машина выдана'), (9, 'Валет сессия завершена'), (10, 'Сессия завершена и оплачена')], default=1),
        ),
    ]
