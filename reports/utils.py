import io
from datetime import datetime
from decimal import Decimal
from typing import Iterable, List

from openpyxl import Workbook

from payments.models import (
    TinkoffPayment,
    PAYMENT_STATUS_CONFIRMED,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_STATUS_PARTIAL_REFUNDED,
)

from .models import Transaction, Report


HEADER = [
    'Date and time',
    'Amount',
    'Transaction type',
    'Commission %',
    'Amount to pay',
]


def generate_excel(report: Report, transactions: Iterable[Transaction]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(HEADER)

    total_income = Decimal('0.00')
    total_refunds = Decimal('0.00')
    total_commission = Decimal('0.00')
    total_payout = Decimal('0.00')

    for tr in transactions:
        commission_amount = tr.commission_amount()
        payout = tr.payout_amount()
        ws.append([
            tr.datetime.strftime('%Y-%m-%d %H:%M'),
            float(tr.amount) if tr.type == tr.TYPE_SUCCESS else -float(tr.amount),
            'Refund' if tr.type == tr.TYPE_REFUND else 'Success',
            float(report.obj.commission) if tr.type == tr.TYPE_SUCCESS else '',
            float(payout),
        ])
        if tr.type == tr.TYPE_REFUND:
            total_refunds += tr.amount
            total_payout -= tr.amount
        else:
            total_income += tr.amount
            total_commission += commission_amount
            total_payout += payout

    ws.append([])
    ws.append(['Total income', float(total_income)])
    ws.append(['Total refunds', float(total_refunds)])
    ws.append(['Total commission', float(total_commission)])
    ws.append(['Total payout', float(total_payout)])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), total_income, total_refunds, total_commission, total_payout


def create_report(obj, from_date: datetime, to_date: datetime) -> Report:
    payments = TinkoffPayment.objects.filter(
        status__in=[
            PAYMENT_STATUS_CONFIRMED,
            PAYMENT_STATUS_REFUNDED,
            PAYMENT_STATUS_PARTIAL_REFUNDED,
        ],
        updated_at__gte=from_date,
        updated_at__lte=to_date,
        order__session__parking__company=obj.company,
    ).select_related('order').order_by('updated_at')

    transactions: List[Transaction] = []
    for pay in payments:
        if pay.status in [PAYMENT_STATUS_REFUNDED, PAYMENT_STATUS_PARTIAL_REFUNDED]:
            tr_type = Transaction.TYPE_REFUND
            amount = pay.order.refunded_sum or pay.order.sum
        else:
            tr_type = Transaction.TYPE_SUCCESS
            amount = pay.order.sum

        tr = Transaction.objects.create(
            obj=obj,
            datetime=pay.updated_at,
            amount=amount,
            type=tr_type,
            status=Transaction.STATUS_CONFIRMED,
        )
        transactions.append(tr)

    report = Report.objects.create(obj=obj, from_date=from_date, to_date=to_date)
    data, income, refunds, commission, payout = generate_excel(report, transactions)

    report.total_income = income
    report.total_refunds = refunds
    report.total_commission = commission
    report.total_payout = payout

    filename = f'report_{report.id}.xlsx'
    report.file.save(filename, io.BytesIO(data))
    report.save()
    return report
