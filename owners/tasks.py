# -*- coding: utf-8 -*-

import logging
import os.path

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from openpyxl import load_workbook

import pandas as pd

from django.utils import timezone

from base.utils import get_logger
from owners.models import CompanySettingReports
from parkings.models import ParkingSession
from parkpass.celery import app
from parkpass.settings import REPORTS_ROOT, EMAIL_HOST_USER
from rps_vendor.models import RpsSubscription, ParkingCard, RpsParkingCardSession, STATE_CONFIRMED


@app.task()
def generate_report_and_send(settings_report_id):
    get_logger().info("generate_report_and_send %s" % settings_report_id)
    try:
        report = CompanySettingReports.objects.select_related(
            'company').select_related('parking').get(id=settings_report_id)
        filename = create_report_for_parking(
            report.parking, report.last_send_date,
            report.last_send_date + report.period_in_days
        )
        send_report(report.report_emails, filename)
    except ObjectDoesNotExist:
        get_logger().warn("CompanySettingReports with id %d is not found" % settings_report_id)


def create_report_for_parking(parking, from_date, to_date):
    sessions = ParkingSession.objects.filter(
        completed_at__gte=from_date,
        started_at__lte=to_date
    )
    parking_cards = RpsParkingCardSession.objects.filter(
        state=STATE_CONFIRMED,
        created_at_gte=from_date,
        created_at__lt=to_date
    ).select_related('parking_card')

    subscriptions = RpsSubscription.objects.filter(
        started_at__gte=from_date,
        started_at__lt=to_date,
        state=STATE_CONFIRMED
    )

    get_logger().info("reports session:%d, cards:%d, subscriptions:%d " % (sessions.count(), parking_cards.count(), subscriptions.count()))

    filename = REPORTS_ROOT + "report-%s(%s-%s).xlsx" % (
        parking.id, from_date, to_date)

    if not os.path.isfile(filename):
        open(filename, 'a').close()

    append_df_to_excel(filename, gen_session_report_df(sessions), "Парковочные сессии", index_key="#")
    append_df_to_excel(filename, gen_parking_card_report_df(parking_cards), "Парковочные карты", index_key="#")
    append_df_to_excel(filename, gen_subscription_report_df(subscriptions), "Абонементы", index_key="#")

    return filename


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
    DURATION_COL = "Продолжительность"
    DEBT_COL = "Стоймость"
    STATE_COL = "Статус"

    propotype = {
        ID_COL: [],
        START_COL: [],
        END_COL: [],
        DURATION_COL: [],
        DEBT_COL: [],
        STATE_COL: [],
    }

    for session in qs:
        propotype[ID_COL].append(session.id)
        propotype[START_COL].append(session.started_at)
        propotype[DURATION_COL].append(session.duration)
        propotype[DEBT_COL].append(session.debt)

        if session.client_state == ParkingSession.CLIENT_STATE_CANCELED:
            propotype[STATE_COL].append("Отменена")

        if session.client_state == ParkingSession.CLIENT_STATE_CLOSED:
            propotype[STATE_COL].append("Оплачена")

        if session.client_state == ParkingSession.CLIENT_STATE_ACTIVE:
            propotype[STATE_COL].append("Активная")

        if session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Приостановлена пользователем")

        if session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Ожидает оплаты")

    return pd.DataFrame(data=propotype)


def gen_parking_card_report_df(qs):
    ID_COL = "#"
    START_COL = "Время въезда"
    END_COL = "Время выезда"
    DURATION_COL = "Продолжительность"
    PRICE_COL = "Стоймость"
    BUY_DATETIME_COL = "Дата оплаты"

    propotype = {
        ID_COL: [],
        START_COL: [],
        END_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
        BUY_DATETIME_COL: []
    }

    for parking_card_session in qs:
        propotype[ID_COL].append(parking_card_session.id)
        propotype[START_COL].append("-")
        propotype[END_COL].append("-")
        propotype[DURATION_COL].append(parking_card_session.duration)
        propotype[PRICE_COL].append(parking_card_session.debt)
        propotype[BUY_DATETIME_COL].append(parking_card_session.created_at)

    return pd.DataFrame(data=propotype)


def gen_subscription_report_df(qs):
    ID_COL = "#"
    VENDOR_ID_COL = "# в системе вендора"
    START_COL = "Время покупки"
    DURATION_COL = "Продолжительность"
    PRICE_COL = "Стоимость абонемента"
    BUY_DATETIME_COL = "Дата покупки"

    propotype = {
        ID_COL: [],
        VENDOR_ID_COL: [],
        START_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
        BUY_DATETIME_COL: []
    }

    for subscription in qs:
        propotype[ID_COL].append(subscription.id)
        propotype[VENDOR_ID_COL].append(subscription.idts)
        propotype[START_COL].append(subscription.started_at)
        propotype[DURATION_COL].append(subscription.duration)
        propotype[PRICE_COL].append(subscription.sum)
        propotype[BUY_DATETIME_COL].append(subscription.started_at)

    return pd.DataFrame(data=propotype)


def append_df_to_excel(filename, df, sheet_name,
                       startrow=None, truncate_sheet=True, index_key=None, **to_excel_kwargs):
    """
    Parameters:
    filename : File path or existing ExcelWriter
             (Example: '/path/to/file.xlsx')
    df : dataframe to save to workbook
    sheet_name : Name of sheet which will contain DataFrame.
               (default: 'Sheet1')
    startrow : upper left cell row to dump data frame.
             Per default (startrow=None) calculate the last row
             in the existing DF and write to the next row...
    truncate_sheet : truncate (remove and recreate) [sheet_name]
                   before writing DataFrame to Excel file
    to_excel_kwargs : arguments which will be passed to `DataFrame.to_excel()`
                    [can be dictionary]

    Returns: None
    """

    # ignore [engine] parameter if it was passed
    if 'engine' in to_excel_kwargs:
        to_excel_kwargs.pop('engine')

    #writer = pd.ExcelWriter(filename, engine='openpyxl')
    writer = pd.ExcelWriter(filename)

    # Python 2.x: define [FileNotFoundError] exception if it doesn't exist
    # try:
    #     FileNotFoundError
    # except NameError:
    #     FileNotFoundError = IOError

    FileNotFoundError = IOError
    try:
        writer.book = load_workbook(filename)
        if startrow is None and sheet_name in writer.book.sheetnames:
            startrow = writer.book[sheet_name].max_row

        # truncate sheet
        if truncate_sheet and sheet_name in writer.book.sheetnames:
            # index of [sheet_name] sheet
            idx = writer.book.sheetnames.index(sheet_name)
            # remove [sheet_name]
            writer.book.remove(writer.book.worksheets[idx])
            # create an empty sheet [sheet_name] using old index
            writer.book.create_sheet(sheet_name, idx)

        # copy existing sheets
        writer.sheets = {ws.title: ws for ws in writer.book.worksheets}

    except FileNotFoundError:
        # TODO write logs if something occurs
        # file does not exist yet, we will create it
        pass

    if startrow is None:
        startrow = 0

    if index_key:
        df.set_index(index_key, inplace=True)

    df.to_excel(writer, sheet_name, startrow=startrow, **to_excel_kwargs)
    writer.save()


@app.task()
def check_send_reports():
    get_logger().info("start checking reports for owners")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)