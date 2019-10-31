# -*- coding: utf-8 -*-
import os.path
from datetime import timedelta

import pandas as pd
import shutil
from openpyxl import load_workbook

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.utils import timezone

from base.utils import get_logger
from owners.models import CompanySettingReports, CompanyReport
from parkings.models import ParkingSession
from parkpass_backend.celery import app
from parkpass_backend.settings import REPORTS_ROOT, EMAIL_HOST_USER, STATIC_ROOT
from rps_vendor.models import RpsSubscription, RpsParkingCardSession, STATE_CONFIRMED


@app.task()
def generate_report_and_send(settings_report_id):
    get_logger().info("generate_report_and_send %s" % settings_report_id)
    try:
        report_settings = CompanySettingReports.objects.select_related(
            'company').select_related('parking').get(id=settings_report_id)

        filename = os.path.join(REPORTS_ROOT, "report-%s-%s_%s.xlsx" % (
            report_settings.parking.id,
            report_settings.last_send_date.date(),
            (report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)).date()
        ))

        report = CompanyReport.objects.filter(filename=filename).first()
        if report:
            get_logger().warning("Report is already exist: %s" % filename)

        else:
            if create_report_for_parking(report_settings.parking, report_settings.last_send_date,
                                         report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)):
                CompanyReport.objects.create(company=report_settings.company, filename=filename)
                send_report(report_settings.report_emails, filename)
                get_logger().info("Report done: %s" % filename)

        report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)
        report_settings.save()

    except ObjectDoesNotExist:
        get_logger().warn("CompanySettingReports with id %d is not found" % settings_report_id)


def test_generate():
    report_settings = CompanySettingReports.objects.select_related(
        'company').select_related('parking').all()[0]

    filename = os.path.join(REPORTS_ROOT, "report-%s-%s_%s.xlsx" % (
        report_settings.parking.id,
        report_settings.last_send_date.date(),
        (report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)).date()
    ))

    create_report_for_parking(
        report_settings.parking,
        report_settings.last_send_date,
        report_settings.last_send_date + timedelta(
            seconds=report_settings.period_in_days * 24 * 60 * 60))


def create_report_for_parking(parking, from_date, to_date):
    sessions = ParkingSession.objects.filter(
        completed_at__gte=from_date,
        started_at__lte=to_date
    )
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

    get_logger().info("reports session:%d, cards:%d, subscriptions:%d " % (
        sessions.count(), parking_cards.count(), subscriptions.count()))

    filename = os.path.join(REPORTS_ROOT, "report-%s-%s_%s.xlsx" % (
        parking.id, from_date.date(), to_date.date()))

    if not os.path.isfile(filename):
        source = os.path.join(STATIC_ROOT, "files/%s" % "report_template_empty.xlsx")
        shutil.copy2(source, filename)

    pages = {
        "Сессии": gen_session_report_df(sessions),
        "Парковочные карты": gen_parking_card_report_df(parking_cards),
        "Абонементы": gen_subscription_report_df(subscriptions)
    }

    append_dfs_to_excel(filename, pages, index_key="#")

    return True


def send_report(emails, filename):
    targets = emails.split(",")
    msg = EmailMessage('Parkpass report', 'Hello. Your report inside...', EMAIL_HOST_USER, targets)
    msg.content_subtype = "html"
    msg.attach_file(filename)
    msg.send()


def gen_session_report_df(qs):
    ID_COL = "#"
    START_COL = "Время въезда"
    END_COL = "Время выезда"
    DURATION_COL = "Продолжительность, сек."
    DEBT_COL = "Стоймость, руб."
    STATE_COL = "Статус"

    propotype = {
        ID_COL: [],
        START_COL: [],
        END_COL: [],
        DURATION_COL: [],
        DEBT_COL: [],
        STATE_COL: [],
    }

    total_sum = 0

    for session in qs:
        propotype[ID_COL].append(session.id)
        propotype[START_COL].append(session.started_at.strftime("%Y-%m-%d %H:%M:%S"))
        propotype[END_COL].append(session.completed_at.strftime("%Y-%m-%d %H:%M:%S"))
        propotype[DURATION_COL].append(session.get_cool_duration())
        propotype[DEBT_COL].append(float(session.debt))

        total_sum += session.debt

        if session.client_state == ParkingSession.CLIENT_STATE_CANCELED:
            propotype[STATE_COL].append("Отменена")

        elif session.client_state == ParkingSession.CLIENT_STATE_CLOSED:
            propotype[STATE_COL].append("Оплачена")

        elif session.client_state == ParkingSession.CLIENT_STATE_ACTIVE:
            propotype[STATE_COL].append("Активная")

        elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Приостановлена")

        elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Ожидает оплаты")
        else:
            propotype[STATE_COL].append("Не определена")

    propotype[ID_COL].extend(["", ""])
    propotype[START_COL].extend(["", ""])
    propotype[END_COL].extend(["", ""])
    propotype[DURATION_COL].extend(["", ""])
    propotype[DEBT_COL].extend(["", "Итог: "])
    propotype[STATE_COL].extend(["", "%s руб." % int(total_sum)])

    return pd.DataFrame(data=propotype)


def gen_parking_card_report_df(qs):
    ID_COL = "#"
    START_COL = "Время въезда"
    END_COL = "Время выезда"
    DURATION_COL = "Продолжительность, сек."
    PRICE_COL = "Стоймость, руб."
    BUY_DATETIME_COL = "Дата и время оплаты"

    propotype = {
        ID_COL: [],
        START_COL: [],
        END_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
        BUY_DATETIME_COL: []
    }

    total_sum = 0

    for parking_card_session in qs:
        propotype[ID_COL].append(parking_card_session.id)

        if parking_card_session.from_datetime:
            propotype[START_COL].append(parking_card_session.from_datetime.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            propotype[START_COL].append('Нет данных')

        propotype[END_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        propotype[DURATION_COL].append(parking_card_session.get_cool_duration())
        propotype[PRICE_COL].append(float(parking_card_session.debt))
        total_sum += parking_card_session.debt
        propotype[BUY_DATETIME_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %H:%M:%S"))

    propotype[ID_COL].extend(["",""])
    propotype[START_COL].extend(["",""])
    propotype[END_COL].extend(["",""])
    propotype[DURATION_COL].extend(["",""])
    propotype[PRICE_COL].extend(["","Итог: "])
    propotype[BUY_DATETIME_COL].extend(["","%s руб." % int(total_sum)])

    get_logger().info(propotype)
    return pd.DataFrame(data=propotype)


def gen_subscription_report_df(qs):
    ID_COL = "#"
    VENDOR_ID_COL = "# системы вендора"
    START_COL = "Время покупки"
    DURATION_COL = "Продолжительность"
    PRICE_COL = "Стоймость, руб."

    propotype = {
        ID_COL: [],
        VENDOR_ID_COL: [],
        START_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
    }

    total_sum = 0

    for subscription in qs:
        propotype[ID_COL].append(subscription.id)
        propotype[VENDOR_ID_COL].append(subscription.idts)
        propotype[START_COL].append(subscription.started_at.strftime("%Y-%m-%d %H:%M:%S"))
        propotype[DURATION_COL].append(subscription.get_cool_duration())
        propotype[PRICE_COL].append(float(subscription.sum))
        total_sum += subscription.sum

    propotype[ID_COL].extend(["", ""])
    propotype[VENDOR_ID_COL].extend(["", ""])
    propotype[START_COL].extend(["", ""])

    propotype[DURATION_COL].extend(["", "Итог: "])
    propotype[PRICE_COL].extend(["", "%s руб." % int(total_sum)])
    return pd.DataFrame(data=propotype)


def highlight_max(x):
    return ['background-color: yellow']


def append_dfs_to_excel(filename, pages,
                       startrow=None, truncate_sheet=True, index_key=None, **to_excel_kwargs):

    writer = pd.ExcelWriter(filename)

    if startrow is None:
        startrow = 0

    for page in pages:

        df = pages[page]
        if index_key:
            df.set_index(index_key, inplace=True)

        df.to_excel(writer, sheet_name=page, startrow=startrow)
        worksheet = writer.sheets[page]
        for idx, col in enumerate(df):
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name)) * 2  # len of column name/header
            )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)  # set column width
    writer.save()


@app.task()
def check_send_reports():
    get_logger().info("start checking reports for owners")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)