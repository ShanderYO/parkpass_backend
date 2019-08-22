import logging

from openpyxl import load_workbook

import pandas as pd

from django.utils import timezone

from owners.models import CompanySettingReports
from parkings.models import ParkingSession
from parkpass.celery import app
from parkpass.settings import REPORTS_ROOT
from rps_vendor.models import RpsSubscription, ParkingCard


@app.task()
def generate_report_and_send(settings_report_id):
    report = CompanySettingReports.objects.select_related('company', 'parking').get(settings_report_id)
    create_report_for_parking(
        report.parking, report.last_send_date,
        report.last_send_date + report.period_in_days
    )


def create_report_for_parking(parking, from_date, to_date):
    sessions = ParkingSession.objects.filter(
        completed_at__gte=from_date,
        started_at__lte=to_date
    )
    # TODO add data of buy
    parking_cards = ParkingCard.objects.filter()

    # TODO add data of buy
    subscriptions = RpsSubscription.objects.filter()

    filename = REPORTS_ROOT + "report-%s(%s-%s).xlsx" % (
        parking.id, from_date, to_date)

    append_df_to_excel(filename, gen_session_report_df(sessions), "Sessions")
    append_df_to_excel(filename, gen_parking_card_report_df(parking_cards), "Parking card")
    append_df_to_excel(filename, gen_subscription_report_df(subscriptions), "Subscriptions")


def gen_session_report_df(qs):
    ID_COL = " #"
    START_COL = "START DATETIME"
    END_COL = "END DATETIME"
    DURATION_COL = "DURATION"
    DEBT_COL = "DEBT"
    STATE_COL = "STATE"

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
        propotype[STATE_COL].append(session.status)

    return pd.DataFrame(data=propotype)


def gen_parking_card_report_df(qs):
    ID_COL = " #"
    START_COL = "START DATETIME"
    END_COL = "END DATETIME"
    DURATION_COL = "DURATION"
    PRICE_COL = "PRICE"

    propotype = {
        ID_COL: [],
        START_COL: [],
        END_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
    }
    return pd.DataFrame(data=propotype)


def gen_subscription_report_df(qs):
    ID_COL = " #"
    VENDOR_ID_COL = "VENDOR #"
    START_COL = "START DATETIME"
    DURATION_COL = "DURATION"
    PRICE_COL = "PRICE"

    propotype = {
        ID_COL: [],
        VENDOR_ID_COL: [],
        START_COL: [],
        DURATION_COL: [],
        PRICE_COL: [],
    }
    return pd.DataFrame(data=propotype)


def append_df_to_excel(filename, df, sheet_name,
                       startrow=None, truncate_sheet=True, **to_excel_kwargs):
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
        # try to open an existing workbook
        writer.book = load_workbook(filename)

        # get the last row in the existing Excel sheet
        # if it was not specified explicitly
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
        # file does not exist yet, we will create it
        pass

    if startrow is None:
        startrow = 0

    # write out the new sheet
    df.to_excel(writer, sheet_name, startrow=startrow, **to_excel_kwargs)

    # save the workbook
    writer.save()


@app.task()
def check_send_reports():
    logging.info("start checking reports for owners")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)