from decimal import Decimal
from payments.models import Order
from rps_vendor.models import RpsParking
from payments_reports.models import ParkingPaymentReport, ParkingPaymentReportTransaction, TransactionType


class OwnersPaymentsReports:
    @classmethod
    def generate_report_for_owner(cls, owner, period_start, period_end):
        configs = owner.report_configs.select_related('parking', 'owner', 'company').all()
        if not configs.exists():
            return None

        report = ParkingPaymentReport.objects.create(
            owner=owner,
            period_start=period_start,
            period_end=period_end,
            total_amount=Decimal('0.0'),
            total_commission=Decimal('0.0'),
            total_refunds=Decimal('0.0'),
            payout_amount=Decimal('0.0'),
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
            rps_parking = RpsParking.objects.get(parking=parking)
        except RpsParking.DoesNotExist:
            return  # пропускаем, если нет RpsParking

        # Смотрим только tinkoff и с терминалом
        orders = Order.objects.filter(
            parking_card_session__parking=rps_parking,
            acquiring='tinkoff',
            terminal__isnull=False,
            created_at__range=(period_start, period_end)
        )

        if not orders.exists():
            return

        total_amount = Decimal('0.0')
        total_count = 0

        for order in orders:
            ParkingPaymentReportTransaction.objects.create(
                report=report,
                parking=parking,  # оригинальный Parking
                amount=order.sum,
                transaction_type=TransactionType.CONFIRMED.value,
                commission_percent=config.commission_percent,
                commission_amount=Decimal('0.0'),  # комиссия, если появится, можно рассчитать
                payout_amount=order.sum,  # пока без комиссии
                paid_at=order.created_at,
            )

            total_amount += order.sum
            total_count += 1

        report.total_amount += total_amount
        # total_refunds и total_commission пока 0, но можно расширить позже
        report.payout_amount = report.total_amount - report.total_refunds - report.total_commission
        report.save()

    @classmethod
    def generate_reports_for_all(cls, period_start, period_end):
        from owners.models import Owner

        for owner in Owner.objects.all():
            cls.generate_report_for_owner(owner, period_start, period_end)
