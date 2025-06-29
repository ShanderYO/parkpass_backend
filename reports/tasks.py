from datetime import timedelta
from django.utils import timezone
from celery import shared_task

from .models import ReportObject
from .utils import create_report


@shared_task
def generate_periodic_reports():
    now = timezone.now()
    for obj in ReportObject.objects.all():
        last = obj.last_report_sent or (now - timedelta(days=obj.period_days))
        if obj.period_type == obj.PERIOD_DAILY:
            step = timedelta(days=1)
        elif obj.period_type == obj.PERIOD_WEEKLY:
            step = timedelta(days=7)
        elif obj.period_type == obj.PERIOD_MONTHLY:
            step = timedelta(days=30)
        else:
            step = timedelta(days=obj.period_days)

        if now - last >= step:
            report = create_report(obj, last, now)
            obj.last_report_sent = now
            obj.save()
            # sending logic can be implemented here
            _ = report
