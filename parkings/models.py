from django.db import models


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
        print lt_point[0], rb_point[0]
        print lt_point[1], rb_point[1]
        result = Parking.objects.filter(
            latitude__range=[rb_point[0], lt_point[0]],
            longitude__range=[lt_point[1], rb_point[1]],
            enabled=True
        )
        return result