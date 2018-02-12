from django.db import models

from accounts.models import Account

class Parking(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=63, null=True, blank=True)
    description = models.TextField()
    address = models.CharField(max_length=63, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    enabled = models.BooleanField(default=True)
    free_places = models.IntegerField()
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking'
        verbose_name_plural = 'Parkings'

    def __unicode__(self):
        return "%s [%s]" % (self.name, self.id)

    @classmethod
    def find_between_point(cls, lt_point, rb_point):
        result = Parking.objects.filter(
            latitude__range=[rb_point[0], lt_point[0]],
            longitude__range=[lt_point[1], rb_point[1]],
            enabled=True
        )
        return result


# TODO активные сессии
class ParkingSession(models.Model):
    STATE_SESSION_CANCELED = -1
    STATE_SESSION_STARTED = 0
    STATE_SESSION_UPDATED = 1
    STATE_SESSION_COMPLETED = 2

    SESSION_STATES = [
        STATE_SESSION_CANCELED, STATE_SESSION_STARTED, STATE_SESSION_UPDATED, STATE_SESSION_COMPLETED
    ]

    id = models.CharField(primary_key=True, unique=True)

    client = models.ForeignKey(Account)
    parking = models.ForeignKey(Parking)

    is_paused = models.BooleanField(default=False)

    debt = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    state = models.IntegerField(default=STATE_SESSION_STARTED)

    started_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    created_at = models.DateField(auto_now_add=True)
