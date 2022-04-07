# Generated by Django 2.2 on 2022-04-07 08:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parkings', '0016_parkingsession_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('comment', models.TextField(blank=True, null=True)),
                ('icon', models.FileField(upload_to='', validators=[django.core.validators.FileExtensionValidator(['png', 'jpg', 'svg'])])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
