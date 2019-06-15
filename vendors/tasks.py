import logging

from parkpass.celery import app

from vendors.models import VendorNotification


@app.task()
def notify_mos_parking():
    logging.info("notify_mos_parking")
    qs = VendorNotification.objects.filter(
        confirmed_at__is_null=True
    )
    for notification in qs:
        notification.process()
