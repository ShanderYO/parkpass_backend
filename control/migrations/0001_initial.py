# Generated by Django 2.1.5 on 2020-01-10 20:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Admin',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('first_name', models.CharField(blank=True, max_length=63, null=True)),
                ('last_name', models.CharField(blank=True, max_length=63, null=True)),
                ('phone', models.CharField(max_length=15)),
                ('sms_code', models.CharField(blank=True, max_length=6, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('password', models.CharField(default='stub', max_length=255)),
                ('avatar', models.CharField(blank=True, max_length=64, null=True)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('email_confirmation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.EmailConfirmation')),
            ],
            options={
                'verbose_name': 'Account',
                'verbose_name_plural': 'Accounts',
                'ordering': ['-id'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AdminSession',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('token', models.CharField(max_length=63)),
                ('expired_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('admin', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='control.Admin')),
            ],
            options={
                'ordering': ['-expired_at'],
                'abstract': False,
            },
        ),
    ]
