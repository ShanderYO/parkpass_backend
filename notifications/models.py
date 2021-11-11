import json

from django.db import models

# Create your models here.
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
    created_at = models.DateTimeField(auto_now_add=True)
    sended_at = models.DateTimeField(null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=(
        ('all', "all"),
    ), default='all')