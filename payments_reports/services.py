from datetime import timedelta
from decimal import Decimal

from payments.models import TinkoffPayment
from payments_reports.models import (
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
)
from payments_reports.models import TransactionType
from django.utils import timezone


class OwnersPaymentsReports:
    @classmethod
    def generate_report_for_owner(cls, owner, period_start, period_end):
        configs = owner.report_configs.select_related("parking").all()

        if not configs.exists():
            return None

        # создаём общий объект отчёта
        report = ParkingPaymentReport.objects.create(
            owner=owner,
            period_start=period_start,
            period_end=period_end,
            total_amount=0,
            total_commission=0,
            total_refunds=0,
            payout_amount=0,
            is_sent=False,
        )

        for config in configs:
            cls._process_parking_config(config, report, period_start, period_end)

        return report

    @classmethod
    def _process_parking_config(cls, config, report, period_start, period_end):
        parking = config.parking

        # здесь важная правка: проверяем, есть ли terminal у parking
        if not hasattr(parking, "terminal") or parking.terminal is None:
            # пропускаем, если нет terminal
            return

        terminal = parking.terminal

        confirmed_payments = TinkoffPayment.objects.filter(
            terminal=terminal,
            status=TransactionType.CONFIRMED.value,
            paid_at__range=(period_start, period_end),
        )

        refund_payments = TinkoffPayment.objects.filter(
            terminal=terminal,
            status=TransactionType.REFUND.value,
            paid_at__range=(period_start, period_end),
        )

        total_amount = Decimal("0.0")
        total_refund = Decimal("0.0")
        total_commission = Decimal("0.0")

        # добавляем подтверждённые платежи
        for payment in confirmed_payments:
            commission = payment.amount * (config.commission_percent / Decimal("100"))
            payout_amount = payment.amount - commission

            ParkingPaymentReportTransaction.objects.create(
                report=report,
                parking=parking,
                amount=payment.amount,
                transaction_type=TransactionType.CONFIRMED.value,
                commission_percent=config.commission_percent,
                commission_amount=commission,
                payout_amount=payout_amount,
                paid_at=payment.paid_at,
            )

            total_amount += payment.amount
            total_commission += commission

        # добавляем возвраты (отрицательные суммы)
        for payment in refund_payments:
            ParkingPaymentReportTransaction.objects.create(
                report=report,
                parking=parking,
                amount=-payment.amount,
                transaction_type=TransactionType.REFUND.value,
                commission_percent=Decimal("0"),
                commission_amount=Decimal("0"),
                payout_amount=-payment.amount,
                paid_at=payment.paid_at,
            )

            total_refund += payment.amount

        # обновляем агрегаты в report
        report.total_amount += total_amount
        report.total_refund += total_refund
        report.total_commission += total_commission
        report.payout_amount = (
            report.total_amount - report.total_refund - report.total_commission
        )
        report.save()

    @classmethod
    def generate_reports_for_all(cls, period_start, period_end):
        from owners.models import Owner

        for owner in Owner.objects.all():
            cls.generate_report_for_owner(owner, period_start, period_end)
