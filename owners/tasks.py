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
from parkpass.celery import app
from parkpass.settings import REPORTS_ROOT, EMAIL_HOST_USER, STATIC_ROOT
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
        "Session": gen_session_report_df(sessions),
        "Cards": gen_parking_card_report_df(parking_cards),
        "Subscriptions": gen_subscription_report_df(subscriptions)
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
    START_COL = "Check-in"#"Время въезда"
    END_COL = "Check-out"#"Время выезда"
    DURATION_COL = "Duration"#"Продолжительность"
    DEBT_COL = "Debt"#"Стоймость"
    STATE_COL = "State"#"Статус"

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
        propotype[START_COL].append(session.started_at.strftime("%Y-%m-%d %I:%M:%S %p"))
        propotype[END_COL].append(session.completed_at.strftime("%Y-%m-%d %I:%M:%S %p"))
        propotype[DURATION_COL].append(session.get_cool_duration())
        propotype[DEBT_COL].append(float(session.debt))

        if session.client_state == ParkingSession.CLIENT_STATE_CANCELED:
            propotype[STATE_COL].append("Canceled")

        elif session.client_state == ParkingSession.CLIENT_STATE_CLOSED:
            propotype[STATE_COL].append("Paid")

        elif session.client_state == ParkingSession.CLIENT_STATE_ACTIVE:
            propotype[STATE_COL].append("Active")

        elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Suspended")

        elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
            propotype[STATE_COL].append("Waited pay")
        else:
            propotype[STATE_COL].append("Unknown")

    return pd.DataFrame(data=propotype)


def gen_parking_card_report_df(qs):
    ID_COL = "#"
    START_COL = "Check-in"#"Время въезда"
    END_COL = "Check-out"#"Время выезда"
    DURATION_COL = "Duration" #"Продолжительность"
    PRICE_COL = "Debt" #"Стоймость"
    BUY_DATETIME_COL = "Paid at" # "Дата оплаты"

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

        if parking_card_session.from_datetime:
            propotype[START_COL].append(parking_card_session.from_datetime.strftime("%Y-%m-%d %I:%M:%S %p"))
        else:
            propotype[START_COL].append('No data')

        propotype[END_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %I:%M:%S %p"))
        propotype[DURATION_COL].append(parking_card_session.get_cool_duration())
        propotype[PRICE_COL].append(float(parking_card_session.debt))
        propotype[BUY_DATETIME_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %I:%M:%S %p"))

    get_logger().info(propotype)
    return pd.DataFrame(data=propotype)


def gen_subscription_report_df(qs):
    ID_COL = "#"
    VENDOR_ID_COL = "Vendor #" #"# в системе вендора"
    START_COL = "Paid at" # "Время покупки"
    DURATION_COL = "Duration" #"Продолжительность"
    PRICE_COL = "Debt" #"Стоймость"

    propotype = {
        ID_COL: [],
        VENDOR_ID_COL: [],
        START_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
    }

    for subscription in qs:
        propotype[ID_COL].append(subscription.id)
        propotype[VENDOR_ID_COL].append(subscription.idts)
        propotype[START_COL].append(subscription.started_at)
        propotype[DURATION_COL].append(subscription.duration)
        propotype[PRICE_COL].append(float(subscription.sum))

    return pd.DataFrame(data=propotype)


def append_dfs_to_excel(filename, pages,
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

    writer = pd.ExcelWriter(filename, engine='openpyxl')

    # Python 2.x: define [FileNotFoundError] exception if it doesn't exist
    # try:
    #     FileNotFoundError
    # except NameError:
    #     FileNotFoundError = IOError

    FileNotFoundError = IOError
    try:
        writer.book = load_workbook(filename)
        """
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
        """

    except FileNotFoundError:
        # TODO write logs if something occurs
        # file does not exist yet, we will create it
        pass

    if startrow is None:
        startrow = 0

    for page in pages:
        df = pages[page]
        if index_key:
            df.set_index(index_key, inplace=True)
        df.to_excel(writer, page, startrow=startrow, **to_excel_kwargs)

    writer.save()


@app.task()
def check_send_reports():
    get_logger().info("start checking reports for owners")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)