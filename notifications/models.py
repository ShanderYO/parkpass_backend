import json

from django.db import models

# Create your models here.
from django import forms
from fcm_django.models import FCMDevice

from accounts.models import Account


class AccountDevice(FCMDevice):
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'


class Mailing(models.Model):
    title = models.CharField(max_length=360)
    text = models.TextField()
    user_ids = models.TextField(help_text="comma separate", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sended_at = models.DateTimeField(null=True, blank=True)
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE, null=True, blank=True, help_text='Если выбрана парковка, уведомления будут слаться по юзерам из данного объекта')
    parkings_sessions_date = models.DateField(blank=True, null=True, help_text='Формат - YYYY-MM-DD')
    user_type = models.CharField(max_length=10, choices=(
        ('all', "all"),
    ), default='all')