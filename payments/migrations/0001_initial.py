# Generated by Django 2.1.5 on 2020-01-10 20:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('base', '0001_initial'),
        ('rps_vendor', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditCard',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('card_id', models.IntegerField(default=1)),
                ('pan', models.CharField(blank=True, max_length=31)),
                ('exp_date', models.CharField(blank=True, max_length=61)),
                ('is_default', models.BooleanField(default=False)),
                ('rebill_id', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credit_cards', to='accounts.Account')),
            ],
            options={
                'verbose_name': 'CreditCard',
                'verbose_name_plural': 'CreditCards',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='FiskalNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fiscal_number', models.IntegerField()),
                ('shift_number', models.IntegerField()),
                ('receipt_datetime', models.DateTimeField()),
                ('fn_number', models.CharField(max_length=20)),
                ('ecr_reg_number', models.CharField(max_length=20)),
                ('fiscal_document_number', models.IntegerField()),
                ('fiscal_document_attribute', models.BigIntegerField()),
                ('ofd', models.TextField(blank=True, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('qr_code_url', models.URLField(blank=True, null=True)),
                ('receipt', models.TextField()),
                ('card_pan', models.CharField(max_length=31)),
                ('type', models.CharField(max_length=15)),
            ],
            options={
                'ordering': ['-receipt_datetime'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('sum', models.DecimalField(decimal_places=2, max_digits=8)),
                ('payment_attempts', models.PositiveSmallIntegerField(default=1)),
                ('authorized', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('paid_card_pan', models.CharField(default='', max_length=31)),
                ('refund_request', models.BooleanField(default=False)),
                ('refunded_sum', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_notified_at', models.DateTimeField(blank=True, null=True)),
                ('client_uuid', models.UUIDField(default=None, null=True)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Account')),
                ('fiscal_notification', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='payments.FiskalNotification')),
                ('parking_card_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rps_vendor.RpsParkingCardSession')),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parkings.ParkingSession')),
            ],
            options={
                'verbose_name': 'Order',
                'verbose_name_plural': 'Orders',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TinkoffPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_id', models.BigIntegerField(blank=True, null=True, unique=True)),
                ('status', models.SmallIntegerField(choices=[(-1, 'Unknown'), (0, 'Init'), (1, 'New'), (2, 'Cancel'), (3, 'Form showed'), (4, 'Rejected'), (5, 'Auth fail'), (6, 'Authorized'), (7, 'Confirmed'), (9, 'Refunded'), (10, 'Partial_refunded')], default=0)),
                ('receipt_data', models.TextField(blank=True, null=True)),
                ('error_code', models.IntegerField(default=-1)),
                ('error_message', models.CharField(blank=True, max_length=127, null=True)),
                ('error_description', models.TextField(blank=True, max_length=511, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='payments.Order')),
            ],
            options={
                'verbose_name': 'Tinkoff Payment',
                'verbose_name_plural': 'Tinkoff Payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
