# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RpsPaymentTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.IntegerField(help_text='ID заказа')),
                ('rps_parking_id', models.IntegerField(help_text='ID RPS парковки')),
                ('card_id', models.CharField(help_text='ID карты', max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Сумма оплаты', max_digits=10)),
                ('status', models.CharField(choices=[('created', 'Создана'), ('in_process', 'В процессе'), ('successful', 'Успешно'), ('failed', 'Ошибка')], default='created', help_text='Статус задачи', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Сообщение об ошибке', null=True)),
                ('last_error', models.TextField(blank=True, help_text='Последняя ошибка', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Время создания')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Время обновления')),
                ('processed_at', models.DateTimeField(blank=True, help_text='Время обработки', null=True)),
                ('attempts_count', models.PositiveIntegerField(default=0, help_text='Количество попыток')),
                ('max_attempts', models.PositiveIntegerField(default=3, help_text='Максимальное количество попыток')),
            ],
            options={
                'verbose_name': 'Задача отправки оплаты на RPS',
                'verbose_name_plural': 'Задачи отправки оплаты на RPS',
                'db_table': 'integration_rps_payment_task',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='rpspaymenttask',
            index=models.Index(fields=['status', 'created_at'], name='integration_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='rpspaymenttask',
            index=models.Index(fields=['order_id'], name='integration_order_id_idx'),
        ),
        migrations.AddIndex(
            model_name='rpspaymenttask',
            index=models.Index(fields=['rps_parking_id'], name='integration_rps_parking_id_idx'),
        ),
    ]
