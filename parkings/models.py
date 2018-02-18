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


class ParkingSession(models.Model):
    STATE_SESSION_CANCELED = -1
    STATE_SESSION_STARTED = 0
    STATE_SESSION_UPDATED = 1
    STATE_SESSION_COMPLETED = 2

    SESSION_STATES = [
        STATE_SESSION_CANCELED, STATE_SESSION_STARTED, STATE_SESSION_UPDATED, STATE_SESSION_COMPLETED
    ]

    STATE_CHOICES = (
        (STATE_SESSION_CANCELED, 'Canceled'),
        (STATE_SESSION_STARTED, 'Started'),
        (STATE_SESSION_UPDATED, 'Updated'),
        (STATE_SESSION_COMPLETED, 'Completed'),  # extensible.
    )

    id = models.AutoField(unique=True, primary_key=True)
    session_id = models.CharField(max_length=64)

    client = models.ForeignKey(Account)
    parking = models.ForeignKey(Parking)

    is_paused = models.BooleanField(default=False)

    debt = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_SESSION_STARTED)

    started_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'Parking Session'
        verbose_name_plural = 'Parking Sessions'
        unique_together = ("session_id", "parking")

    def __unicode__(self):
        return "%s [%s]" % (self.parking.id, self.client.id)