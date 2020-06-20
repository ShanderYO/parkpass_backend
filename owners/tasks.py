# -*- coding: utf-8 -*-
import os.path
import subprocess
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.utils import timezone

from base.utils import get_logger
from owners.models import CompanySettingReports, CompanyReport
from owners.utils import caret_mover
from parkings.models import ParkingSession
from parkpass_backend.celery import app
from parkpass_backend.settings import REPORTS_ROOT, EMAIL_HOST_USER
from payments.models import InvoiceWithdraw
from rps_vendor.models import RpsSubscription, RpsParkingCardSession, STATE_CONFIRMED


MAX_ROWS_IN_SHEET=1000


@app.task()
def check_send_reports():
    get_logger().info("Start checking reports for owners...")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)


@app.task()
def generate_report_and_send(settings_report_id):
    get_logger().info("Start generate report for id=%s" % settings_report_id)
    try:
        report_settings = CompanySettingReports.objects.select_related(
            'company').select_related('parking').get(id=settings_report_id)

        from_date = report_settings.last_send_date
        to_date = report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)

        filepath = make_dir_for_report(report_settings.parking.id, from_date, report_settings.period_in_days)

        report = CompanyReport.objects.filter(filename=filepath).first()
        if report:
            get_logger().warning("Report is already exist: %s" % filepath)
            return

        sessions = ParkingSession.objects.filter(
            completed_at__gte=from_date,
            started_at__lte=to_date)

        parking_cards = RpsParkingCardSession.objects.filter(
            state=STATE_CONFIRMED,
            created_at__gte=from_date,
            created_at__lt=to_date
        ).select_related('parking_card')

        subscriptions = RpsSubscription.objects.filter(
            started_at__gte=from_date,
            started_at__lt=to_date,
            state=STATE_CONFIRMED
        )

        total_sum, status = create_report_for_parking(
            filepath, sessions, parking_cards, subscriptions)

        if status:
            report = CompanyReport.objects.create(
                company=report_settings.company,
                filename=filepath
            )
            send_report(report_settings.report_emails, filepath)
            get_logger().info("Report done: %s" % filepath)

            # create_withdraw_request(report, sum=total_sum)

            report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)
            report_settings.save()

        else:
            get_logger().warn("Report generate error: %s" % filepath)

    except ObjectDoesNotExist:
        get_logger().warn("CompanySettingReports with id %d is not found" % settings_report_id)


def send_report(emails, filename):
    targets = emails.split(",")
    msg = EmailMessage('Parkpass report', 'Hello. Your report inside...', EMAIL_HOST_USER, targets)
    msg.content_subtype = "html"
    msg.attach_file(filename)
    msg.send()


def create_withdraw_request(report, sum=0):
    recipient_name = report.company.name
    inn = report.company.inn
    kpp = report.company.kpp
    account_number = report.company.account
    bank_acnt = report.company.bank
    bank_bik = report.company.bik
    payment_purpose = "Регулярная выплата"

    if all([recipient_name, inn, kpp, account_number, bank_acnt, bank_bik, payment_purpose]):
        invoice = InvoiceWithdraw.objects.create(
            amount=sum,
            recipientName=recipient_name,
            inn=inn,
            kpp=kpp,
            accountNumber=account_number,
            bankAcnt=bank_acnt,
            bankBik=bank_bik,
            paymentPurpose=payment_purpose,
            executionOrder=1
        )
        report.invoice_withdraw = invoice
        report.save()
    else:
        get_logger().warn("Company has no valid requisites %s"
                          % [recipient_name, inn, kpp, account_number, bank_acnt, bank_bik, payment_purpose])


def create_report_for_parking(filepath, sessions, parking_cards, subscriptions):
    get_logger().info("reports session:%d, cards:%d, subscriptions:%d " % (
        sessions.count(), parking_cards.count(), subscriptions.count()))

    parking_card_sum = write_cards(filepath, parking_cards)
    session_sum = write_session(filepath, sessions)
    subscription_sum = write_subscriptions(filepath, subscriptions)

    write(filepath) # Fill xlsm file

    total_sum = session_sum + parking_card_sum + subscription_sum
    return total_sum, True


def make_dir_for_report(paring_id, last_send_date, period_in_days):
    """Create empty file to work with
        directory looks like this
        - media
            - reports
                - report_<datetime>.xlsm
                - sheets
            ...
    """
    report_dir = os.path.join(REPORTS_ROOT, "report-%s-%s_%s" % (
        paring_id,
        last_send_date.date(),
        (last_send_date + timedelta(seconds=period_in_days * 24 * 60 * 60)).date()
    ))

    try:
        os.mkdir(report_dir)
        os.mkdir(os.path.join(report_dir, 'sheets'))
    except FileExistsError:
        pass

    return report_dir


def write_session(filepath, qs):
    total_sum = 0
    with open(filepath + '/sheets/' + 'Сессии', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        for session in qs:
            status_str = ""

            if session.client_state == ParkingSession.CLIENT_STATE_CANCELED:
                status_str = "Отменена"

            elif session.client_state == ParkingSession.CLIENT_STATE_CLOSED:
                total_sum += float(session.debt)
                status_str = "Оплачена"

            elif session.client_state == ParkingSession.CLIENT_STATE_ACTIVE:
                status_str = "Активная"

            elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
                status_str = "Приостановлена"

            elif session.state in [
                ParkingSession.STATE_COMPLETED_BY_VENDOR_FULLY,
                ParkingSession.STATE_COMPLETED,
                ParkingSession.CLIENT_STATE_SUSPENDED]:
                status_str = "Ожидает оплаты"

            else:
                status_str = "Не определен"

            f.write('\x1d\x1d{id}\x1d{started_at}\x1d{completed_at}\x1d{duration}\x1d{sum}\x1d{state}'.format(
                id=session.id,
                started_at=session.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                completed_at=session.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                duration=session.get_cool_duration(),
                sum=float(session.debt),
                state=status_str
            ))
            move_down()

        rows = qs.count()
        move_down(MAX_ROWS_IN_SHEET - rows)
        f.write('\x1d\x1d\x1d\x1d\x1d\x1d{total} руб.'.format(total=total_sum))

    return total_sum


def write_cards(filepath, qs):
    total_sum = 0
    with open(filepath + '/sheets/' + 'Карты', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        for parking_card_session in qs:
            paid_at = parking_card_session.from_datetime.strftime("%Y-%m-%d %H:%M:%S") \
                if parking_card_session.from_datetime else 'н/д'

            f.write('\x1d\x1d{id}\x1d{paid_at}\x1d{duration}\x1d{sum}'.format(
                id=parking_card_session.id,
                paid_at=paid_at,
                duration=parking_card_session.get_cool_duration(),
                sum=float(parking_card_session.debt)
            ))
            total_sum += parking_card_session.debt

        rows = qs.count()
        move_down(MAX_ROWS_IN_SHEET - rows)
        f.write('\x1d\x1d\x1d\x1d{total} руб.'.format(total=total_sum))

    return total_sum


def write_subscriptions(filepath, qs):
    total_sum = 0
    with open(filepath + '/sheets/' + 'Подписки', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        for subscription in qs:
            f.write('\x1d{id}\x1d{sum}\x1d{duration}\x1d{started_at}\x1d{vendor_idts}'.format(
                id=subscription.id,
                sum=float(subscription.sum),
                duration=subscription.get_cool_duration(),
                started_at=subscription.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                vendor_idts=subscription.idts,
            ))
            total_sum += subscription.sum
            move_down()

        rows = qs.count()
        move_down(MAX_ROWS_IN_SHEET - rows)
        f.write('\x1d\x1d{total} руб. '.format(total=total_sum))

    return total_sum


def write(filepath):
    filename = filepath + '/report.xlsm'
    subprocess.run(["./lib/OpenXLSX/install/bin/Demo1", filepath + '/sheets', filename])
