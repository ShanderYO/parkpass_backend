# Generated by Django 2.2 on 2022-04-30 09:59

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_country_slug'),
        ('owners', '0021_remove_companyusersrole_type'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='companyuser',
            options={'ordering': ['-id'], 'verbose_name': 'Account', 'verbose_name_plural': 'Accounts'},
        ),
        migrations.AddField(
            model_name='companyuser',
            name='avatar',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='companyuser',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.Country'),
        ),
        migrations.AddField(
            model_name='companyuser',
            name='created_at',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='companyuser',
            name='email_confirmation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.EmailConfirmation'),
        ),
        migrations.AddField(
            model_name='companyuser',
            name='email_fiskal_notification_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='companyuser',
            name='sms_code',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AddField(
            model_name='companyuser',
            name='sms_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='CompanyUserSession',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('token', models.CharField(max_length=63)),
                ('expired_at', models.DateTimeField()),
                ('created_at', models.DateField(auto_now_add=True)),
                ('owner', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='owners.CompanyUser')),
            ],
            options={
                'ordering': ['-expired_at'],
                'abstract': False,
            },
        ),
    ]
