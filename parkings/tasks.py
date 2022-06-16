import asyncio
import datetime
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.utils import timezone

from parkings.models import ParkingSession, ProblemParkingSessionNotifierSettings, ParkingValetSessionRequest
from parkpass_backend.celery import app
from bots.telegram_valet_bot.utils.telegram_valet_bot_utils import send_message_by_valet_bot
from bots.telegram_valetapp_bot.utils.telegram_valetapp_bot_utils import send_message_by_valetapp_bot
from valet.utils.valet_notification_center import ValetNotificationCenter, VALET_NOTIFICATION_REQUEST_FOR_DELIVERY


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
    ).exclude(state=ParkingSession.STATE_CLOSED).select_related('parking')

    settings = ProblemParkingSessionNotifierSettings.objects.first()
    for parking_session in qs:
        if parking_session.state & ParkingSession.COMPLETED_BY_CLIENT_MASK and parking_session.state:
            if parking_session.state & ParkingSession.COMPLETED_BY_VENDOR_MASK:
                continue
            now = timezone.now()
            if (now - parking_session.completed_at) > timezone.timedelta(minutes=settings.interval_in_mins):
                msg = "Обнаружена проблемная сессия parkpass #%s.\n" \
                      "Время выезда клиента %s.\n Время обнаружения %s\n" \
                      "Пользователь: ID=%s, Парковка %s ID=%s" % (
                          parking_session.id,
                          parking_session.completed_at, now,
                          parking_session.client_id,
                          parking_session.parking.name,
                          parking_session.parking.id
                      )
                email = EmailMessage('Проблемная сессия Parkpass', msg, to=settings.report_emails.split(","))
                email.send()
                parking_session.is_send_warning_non_closed_message = True
                parking_session.save()

                settings.last_email_send_date = timezone.now()
                settings.save()


@app.task()
def send_message_by_valet_bots_task(message, chats, company_id, photos, from_valetapp_bot=False):
    if from_valetapp_bot:
        asyncio.get_event_loop().run_until_complete(send_message_by_valetapp_bot(message, company_id, chats, photos))
        # asyncio.run()
    else:
        asyncio.get_event_loop().run_until_complete(send_message_by_valet_bot(message, chats, photos))
        # asyncio.run(send_message_by_valet_bot(message, chats, photos))


@app.task()
def send_book_valet_notifications_if_less_30_minutes():
    now = datetime.datetime.now(timezone.utc)
    now_plus_30 = now + datetime.timedelta(minutes=30)

    requests = ParkingValetSessionRequest.objects.filter(
        finish_time__isnull=True,
        notificated_about_car_book=False,
        car_delivery_time__lte=now_plus_30
    )

    if requests:
        for request in requests:
            ValetNotificationCenter(
                type=VALET_NOTIFICATION_REQUEST_FOR_DELIVERY,
                session=request.valet_session,
                send_email_about_booking_notification=False
            ).run()
