from base.utils import get_logger
from parkpass.celery import app

from vendors.models import VendorNotification


@app.task()
def notify_mos_parking():
    get_logger().info("notify_mos_parking")
    qs = VendorNotification.objects.filter(
        confirmed_at__isnull=True
    )
    for notification in qs:
        notification.process()
