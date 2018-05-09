import datetime
from django.db import models

# Create your models here.
from parkings.models import Parking


class RpsParking(models.Model):
    id = models.AutoField(primary_key=True)
    request_update_url = models.URLField(null=True, blank=True)
    polling_enabled = models.BooleanField(default=False)
    last_request_body = models.TextField(null=True, blank=True)
    last_request_date = models.DateTimeField(default=datetime.datetime.now())

    last_response_code = models.IntegerField(default=0)
    last_response_body = models.TextField(null=True, blank=True)
    parking = models.ForeignKey(Parking)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'RpsParking'
        verbose_name_plural = 'RpsParking'

    def __unicode__(self):
        return "%s" % (self.parking.name)