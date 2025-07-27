from decimal import Decimal
import os

import xlwt

from payments.models import Order
from rps_vendor.models import RpsParking
from payments_reports.models import (
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
    TransactionType,
)


class OwnersPaymentsReports:
    @classmethod
    def generate_report_for_parking(cls, parking, period_start, period_end):
        from payments_reports.models import ParkingReportConfig

        try:
            config = ParkingReportConfig.objects.select_related("owner", "company").get(
                parking=parking
            )
        except ParkingReportConfig.DoesNotExist:
            return None

        report = ParkingPaymentReport.objects.create(
            owner=parking.owner if parking.owner else config.owner,
            parking=parking,
            company=parking.company if parking.company else config.company,
            commission_percent=config.commission_percent,
            period_start=period_start,
            period_end=period_end,
            total_amount=Decimal("0.0"),
            total_commission=Decimal("0.0"),
            total_refunds=Decimal("0.0"),
            payout_amount=Decimal("0.0"),
            is_sent=False,
        )

        cls._process_parking_config(config, report, period_start, period_end)

        return report

    @classmethod
    def _process_parking_config(cls, config, report, period_start, period_end):
        parking = config.parking

        try:
            RpsParking.objects.get(parking=parking)
        except RpsParking.DoesNotExist:
            return

        orders = Order.objects.filter(
            parking_card_session__parking_id=parking.id,
            acquiring="tinkoff",
            terminal__isnull=False,
            created_at__range=(period_start, period_end),
        )

        if not orders.exists():
            return

        transactions = []
        total_amount = Decimal("0.0")
        total_commission = Decimal("0.0")

        for order in orders:
            amount = order.sum
            commission = (
                amount * config.commission_percent / Decimal("100.0")
            ).quantize(Decimal("0.01"))
            amount_after_commission = (amount - commission).quantize(Decimal("0.01"))

            transaction = ParkingPaymentReportTransaction(
                report=report,
                tinkoff_payment=order.tinkoffpayment_set.order_by("id").last(),
                parking=parking,
                date_time=order.created_at,
                amount=amount,
                transaction_type=TransactionType.CONFIRMED.value,
                commission_percent=config.commission_percent,
                amount_after_commission=amount_after_commission,
            )
            transactions.append(transaction)

            total_amount += amount
            total_commission += commission

        ParkingPaymentReportTransaction.objects.bulk_create(transactions)

        report.total_amount = report.total_amount or Decimal("0.00")
        report.total_commission = report.total_commission or Decimal("0.00")
        report.total_refunds = report.total_refunds or Decimal("0.00")

        report.total_amount += total_amount
        report.total_commission += total_commission
        report.payout_amount = (
            report.total_amount - report.total_commission - report.total_refunds
        )
        report.save()

    @classmethod
    def generate_reports_for_all(cls, period_start, period_end):
        from owners.models import Owner

        for owner in Owner.objects.all():
            cls.generate_report_for_owner(owner, period_start, period_end)

    @classmethod
    def export_report_to_xls(cls, report, directory="/tmp"):
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Отчёт")

        # Заголовки таблицы
        headers = [
            "ID транзакции",
            "Парковка",
            "Компания",
            "Дата",
            "Тип",
            "Сумма",
            "Комиссия (%)",
            "Комиссия (₽)",
            "После комиссии",
        ]
        for col, header in enumerate(headers):
            ws.write(0, col, header)

        # Строки с транзакциями
        for row, t in enumerate(report.transactions.all(), start=1):
            ws.write(row, 0, t.id)
            ws.write(row, 1, str(t.parking.name if t.parking else ""))
            ws.write(row, 2, str(report.company.name if report.company else ""))
            ws.write(
                row, 3, t.date_time.strftime("%Y-%m-%d %H:%M:%S") if t.date_time else ""
            )
            ws.write(
                row,
                4,
                (
                    t.get_transaction_type_display()
                    if hasattr(t, "get_transaction_type_display")
                    else t.transaction_type
                ),
            )
            ws.write(row, 5, float(t.amount))
            ws.write(row, 6, float(t.commission_percent or 0))
            ws.write(row, 7, float(t.amount * (t.commission_percent or 0) / 100))
            ws.write(row, 8, float(t.amount_after_commission or 0))

        # Итоговая строка
        summary_row = report.transactions.count() + 1
        ws.write(summary_row, 4, "Итого:")
        ws.write(summary_row, 5, float(report.total_amount or 0))
        ws.write(summary_row, 6, "")
        ws.write(summary_row, 7, float(report.total_commission or 0))
        ws.write(summary_row, 8, float(report.payout_amount or 0))

        path = os.path.join(directory, f"report_{report.id}.xls")
        wb.save(path)
        return path
