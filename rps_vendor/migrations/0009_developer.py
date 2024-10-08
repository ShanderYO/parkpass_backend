# Generated by Django 2.1 on 2021-04-09 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rps_vendor', '0008_rpsparkingcardsession_leave_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Developer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=15, null=True)),
                ('api_key', models.CharField(default='8ed3400f6cc32bf24289a23c33a210198cc46c391a09956b', max_length=256, unique=True)),
                ('developer_id', models.CharField(default='7A0Mgxp5', max_length=128, unique=True)),
                ('is_blocked', models.BooleanField(default=False)),
            ],
        ),
    ]
