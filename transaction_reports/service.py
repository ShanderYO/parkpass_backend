import os
from decimal import Decimal
from django.conf import settings
from openpyxl import Workbook
from payments.models import (
    TinkoffPayment,
    PAYMENT_STATUS_CONFIRMED,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_STATUS_PARTIAL_REFUNDED,
)
from transaction_reports.models import (
    TransactionReport,
    ReportSettings,
    TransactionReportItem,
)


class TransactionReportService:
    def __init__(self, parking):
        self.parking = parking
        self.settings = ReportSettings.objects.get(parking=parking)

    def generate(self, start, end):
        payments = (
            TinkoffPayment.objects.filter(
                order__isnull=False,
                updated_at__gte=start,
                updated_at__lte=end,
            )
            .select_related("order")
            .order_by("updated_at")
        )

        income = Decimal("0")
        refunds = Decimal("0")
        commission = Decimal("0")
        rows = []

        for payment in payments:
            order = payment.order
            if not order:
                continue
            if order.get_parking() != self.parking:
                continue

            amount = order.sum
            if payment.status == PAYMENT_STATUS_CONFIRMED:
                comm = (amount * self.settings.commission_percent) / Decimal("100")
                income += amount
                commission += comm
                pay_amount = amount - comm
                rows.append({
                    "time": payment.updated_at,
                    "amount": amount,
                    "type": TransactionReportItem.TYPE_SUCCESS,
                    "commission": self.settings.commission_percent,
                    "payable": pay_amount,
                })
            elif payment.status in (
                PAYMENT_STATUS_REFUNDED,
                PAYMENT_STATUS_PARTIAL_REFUNDED,
            ):
                refunds += amount
                rows.append({
                    "time": payment.updated_at,
                    "amount": -amount,
                    "type": TransactionReportItem.TYPE_REFUND,
                    "commission": None,
                    "payable": -amount,
                })

        payable = income - commission - refunds

        report = TransactionReport.objects.create(
            parking=self.parking,
            start=start,
            end=end,
            total_income=income,
            total_refund=refunds,
            total_commission=commission,
            total_payable=payable,
        )

        items = []
        for row in rows:
            item = TransactionReportItem.objects.create(
                report=report,
                payment_time=row["time"],
                amount=row["amount"],
                type=row["type"],
                commission_percent=row["commission"],
                payable_amount=row["payable"],
            )
            items.append(item)

        path = self._create_excel(report, items)
        report.file_path = path
        report.save()
        return report

    def _create_excel(self, report, items):
        wb = Workbook()
        ws = wb.active
        ws.append(["Дата и время", "Сумма", "Тип", "Процент комиссии", "Сумма к оплате"])
        for item in items:
            ws.append(
                [
                    item.payment_time,
                    item.amount,
                    item.type,
                    item.commission_percent if item.commission_percent is not None else '-',
                    item.payable_amount,
                ]
            )

        ws.append([])
        ws.append(["", "Общая сумма поступлений", report.total_income])
        ws.append(["", "Общая сумма возвратов", report.total_refund])
        ws.append(["", "Общая сумма удержанной комиссии", report.total_commission])
        ws.append(["", "Итого к выплате", report.total_payable])

        directory = os.path.join(settings.REPORTS_ROOT, "transactions")
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = f"report_{report.id}.xlsx"
        path = os.path.join(directory, filename)
        wb.save(path)
        return path
