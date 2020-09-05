import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.utils import timezone

from parkings.models import ParkingSession, ProblemParkingSessionNotifierSettings
from parkpass_backend.celery import app


@app.task()
def process_updated_sessions(parking_id, sessions):
    try:
        parking = ParkingSession.objects.get(id=parking_id)
    except ObjectDoesNotExist:
        return None

    for session in sessions:
        session_id = session["session_id"]
        debt = int(session["debt"])
        updated_at = int(session["updated_at"])

        utc_updated_at = parking.get_utc_parking_datetime(updated_at)

        parking_sessions = ParkingSession.objects.filter(
            session_id=session_id, parking=parking)

        if parking_sessions.count() > 0:
            parking_session = parking_sessions[0]
            if not parking_sessions.is_available_for_vendor_update():
                continue

            parking_session.debt = debt
            parking_session.updated_at = utc_updated_at
            logging.info("Updated sessions for time %s:" % str(utc_updated_at))
            parking_session.save()


@app.task()
def check_non_closed_vendor_session():
    qs = ParkingSession.objects.filter(
        completed_at__isnull=False,
        is_send_warning_non_closed_message=False
    ).exclude(state=ParkingSession.STATE_CLOSED)

    settings = ProblemParkingSessionNotifierSettings.objects.first()
    for parking_session in qs:
        if parking_session.state & ParkingSession.COMPLETED_BY_CLIENT_MASK and parking_session.state:
            if parking_session.state & ParkingSession.COMPLETED_BY_VENDOR_MASK:
                continue
            now = timezone.now()
            if (now - parking_session.completed_at) > timezone.timedelta(minutes=settings.interval_in_mins):
                msg = "Проблемная сессия parkpass #%s. Время выезда клиента %s. Время обнаружения %s" % (
                    parking_session.id, parking_session.completed_at, now)
                print(msg)
                email = EmailMessage('Пробемная сессия Parkpass', msg, to=settings.report_emails.split(","))
                email.send()
                parking_session.is_send_warning_non_closed_message = True
                parking_session.save()

                settings.last_email_send_date = timezone.now()
                settings.save()
                return