from decimal import Decimal
from payments.models import Order
from rps_vendor.models import RpsParking
from payments_reports.models import (
    ParkingPaymentReport,
    ParkingPaymentReportTransaction,
    TransactionType,
)


class OwnersPaymentsReports:
    @classmethod
    def generate_report_for_owner(cls, owner, period_start, period_end):
        configs = owner.report_configs.select_related(
            "parking", "owner", "company"
        ).all()
        if not configs.exists():
            return None

        report = ParkingPaymentReport.objects.create(
            owner=owner,
            period_start=period_start,
            period_end=period_end,
            total_amount=Decimal("0.0"),
            total_commission=Decimal("0.0"),
            total_refunds=Decimal("0.0"),
            payout_amount=Decimal("0.0"),
            is_sent=False,
        )

        for config in configs:
            cls._process_parking_config(config, report, period_start, period_end)

        return report

    @classmethod
    def _process_parking_config(cls, config, report, period_start, period_end):
        parking = config.parking

        # Берём только RpsParking
        try:
            RpsParking.objects.get(parking=parking)
        except RpsParking.DoesNotExist:
            return  # пропускаем, если нет RpsParking

        # Смотрим только tinkoff и с терминалом
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
