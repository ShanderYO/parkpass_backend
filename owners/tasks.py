# -*- coding: utf-8 -*-
import os.path
import subprocess
from datetime import timedelta

# import pandas as pd
import shutil

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.utils import timezone

from base.utils import get_logger
from owners.models import CompanySettingReports, CompanyReport
from parkings.models import ParkingSession
from parkpass_backend.celery import app
from parkpass_backend.settings import REPORTS_ROOT, EMAIL_HOST_USER, STATIC_ROOT, MEDIA_ROOT
from payments.models import InvoiceWithdraw
from rps_vendor.models import RpsSubscription, RpsParkingCardSession, STATE_CONFIRMED


@app.task()
def generate_report_and_send(settings_report_id):
    get_logger().info("generate_report_and_send %s" % settings_report_id)
    try:
        report_settings = CompanySettingReports.objects.select_related(
            'company').select_related('parking').get(id=settings_report_id)

        sessions = ParkingSession.objects.filter(
            completed_at__isnull=False
        )
        parking_cards = RpsParkingCardSession.objects.filter()

        subscriptions = RpsSubscription.objects.filter()

        filepath = __make_file_for_report(report_settings)

        __write_cards(filepath, parking_cards)
        __write_session(filepath, sessions)
        __write_subscriptions(filepath, subscriptions)

        write(filepath)
        return

        #
        # report = CompanyReport.objects.filter(filename=filepath).first()
        # if report:
        #     get_logger().warning("Report is already exist: %s" % filepath)
        #
        # else:
        #     total_sum, status = create_report_for_parking(
        #         report_settings.parking,
        #         report_settings.last_send_date,
        #         report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)
        #     )
        #
        #     if status:
        #         report = CompanyReport.objects.create(
        #             company=report_settings.company,
        #             filename=filepath
        #         )
        #         send_report(report_settings.report_emails, filepath)
        #         get_logger().info("Report done: %s" % filepath)
        #
        #         recipient_name = report.company.name
        #         inn = report.company.inn
        #         kpp = report.company.kpp
        #         account_number = report.company.account
        #         bank_acnt = report.company.bank
        #         bank_bik = report.company.bik
        #         payment_purpose = "Плановая выплата"
        #
        #         if all([recipient_name, inn, kpp, account_number, bank_acnt, bank_bik, payment_purpose]):
        #             invoice = InvoiceWithdraw.objects.create(
        #                 amount=total_sum,
        #                 recipientName=recipient_name,
        #                 inn=inn,
        #                 kpp=kpp,
        #                 accountNumber=account_number,
        #                 bankAcnt=bank_acnt,
        #                 bankBik=bank_bik,
        #                 paymentPurpose=payment_purpose,
        #                 executionOrder=1
        #             )
        #             report.invoice_withdraw = invoice
        #             report.save()
        #         else:
        #             get_logger().warn("Company has no valid requisites %s"
        #                               % [recipient_name, inn, kpp, account_number, bank_acnt, bank_bik, payment_purpose])
        #
        # report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)
        # report_settings.save()

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

    session_df, session_sum = gen_session_report_df_and_sum(sessions)
    parking_card_df, parking_card_sum = gen_parking_card_report_df_and_sum(parking_cards)
    subscriptions_df, subscription_sum = gen_subscription_report_df_and_sum(subscriptions)

    pages = {
        "Сессии": session_df,
        "Парковочные карты": parking_card_df,
        "Абонементы": subscriptions_df
    }

    # append_dfs_to_excel(filename, pages, index_key="#")

    total_sum = session_sum + parking_card_sum + subscription_sum

    return total_sum, True


def send_report(emails, filename):
    targets = emails.split(",")
    msg = EmailMessage('Parkpass report', 'Hello. Your report inside...', EMAIL_HOST_USER, targets)
    msg.content_subtype = "html"
    msg.attach_file(filename)
    msg.send()


def gen_session_report_df_and_sum(qs):
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

    # return pd.DataFrame(data=propotype), int(total_sum)


def gen_parking_card_report_df_and_sum(qs):
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
    #return pd.DataFrame(data=propotype), int(total_sum)


def gen_subscription_report_df_and_sum(qs):
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

    #return pd.DataFrame(data=propotype), int(total_sum)


def highlight_max(x):
    return ['background-color: yellow']


# def append_dfs_to_excel(filename, pages,
#                        startrow=None, truncate_sheet=True, index_key=None, **to_excel_kwargs):
#
#     writer = pd.ExcelWriter(filename)
#
#     if startrow is None:
#         startrow = 0
#
#     for page in pages:
#         df = pages[page]
#         if index_key:
#             df.set_index(index_key, inplace=True)
#
#         df.to_excel(writer, sheet_name=page, startrow=startrow)
#     writer.save()


@app.task()
def check_send_reports():
    get_logger().info("start checking reports for owners")
    qs = CompanySettingReports.objects.filter(available=True)
    for settings in qs:
        if (timezone.now() - settings.last_send_date).days > settings.period_in_days:
            generate_report_and_send.delay(settings.id)


def caret_mover(fs):
    cur_row = 1

    def inner_func(count=1, with_white_space=False):
        nonlocal cur_row, fs
        for i in range(count):
            fs.write('{}\x0c'.format('\x1d' * 8 + ' ' if with_white_space else ''))
            cur_row += 1
        return cur_row

    return inner_func


def __make_file_for_report(report_settings):
    """Create empty file to work with
        directory looks like this
        - media
            - reports
                - report_<datetime>.xlsm
                - sheets
            ...
    """

    report_dir = os.path.join(REPORTS_ROOT, "report-%s-%s_%s" % (
        report_settings.parking.id,
        report_settings.last_send_date.date(),
        (report_settings.last_send_date + timedelta(seconds=report_settings.period_in_days * 24 * 60 * 60)).date()
    ))

    shutil.rmtree(report_dir, ignore_errors=True)

    try:
        os.mkdir(report_dir)
    except FileExistsError:
        pass

    #os.mkdir(os.path.join(report_dir, 'report.xlsx'))
    os.mkdir(os.path.join(report_dir, 'sheets'))

    return report_dir


def __write_session(filepath, qs):
    with open(filepath + '/sheets/' + 'Сессии', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        total_sum = 0

        for session in qs:
            total_sum += session.debt
            status_str = ""

            if session.client_state == ParkingSession.CLIENT_STATE_CANCELED:
                status_str = "Отменена"

            elif session.client_state == ParkingSession.CLIENT_STATE_CLOSED:
                status_str = "Оплачена"

            elif session.client_state == ParkingSession.CLIENT_STATE_ACTIVE:
                status_str = "Активная"

            elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
                status_str = "Приостановлена"

            elif session.client_state == ParkingSession.CLIENT_STATE_SUSPENDED:
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

        move_down(1000-qs.count())
        f.write('\x1d\x1d\x1d\x1d\x1d\x1d{total}'.format(total=total_sum))


def __write_cards(filepath, qs):
    with open(filepath + '/sheets/' + 'Карты', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        total_sum = 0

        for session in qs:
            total_sum += session.debt
            status_str = ""

            # propotype[ID_COL].append(parking_card_session.id)
            #
            # if parking_card_session.from_datetime:
            #     propotype[START_COL].append(parking_card_session.from_datetime.strftime("%Y-%m-%d %H:%M:%S"))
            # else:
            #     propotype[START_COL].append('Нет данных')
            #
            # propotype[END_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            # propotype[DURATION_COL].append(parking_card_session.get_cool_duration())
            # propotype[PRICE_COL].append(float(parking_card_session.debt))
            # total_sum += parking_card_session.debt
            # propotype[BUY_DATETIME_COL].append(parking_card_session.created_at.strftime("%Y-%m-%d %H:%M:%S"))


def __write_subscriptions(filepath, qs):
    with open(filepath + '/sheets/' + 'Подписки', 'w') as f:
        move_down = caret_mover(f)
        move_down(4)

        total_sum = 0

        for subscription in qs:
            f.write('\x1d{id}\x1d{sum}\x1d{duration}\x1d{started_at}\x1d{vendor_idts}'.format(
                id=subscription.id,
                sum=float(subscription.sum),
                duration=subscription.get_cool_duration(),
                started_at=subscription.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                vendor_idts=subscription.idts,
            ))
            move_down()

        f.write('\x1d\x1d{total} руб. '.format(total=total_sum))


def write(filepath):
    filename = filepath + '/report.xlsm'
    print(filepath)
    print(filename)
    subprocess.run(["./lib/OpenXLSX/install/bin/Demo1", filepath + '/sheets', filename])
