from django.utils import timezone
from django.db.models import Sum, Count
from rps_vendor.models import RpsParking, Order

start_date = timezone.datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
end_date = timezone.datetime(2025, 7, 31, 23, 59, 59, tzinfo=timezone.utc)

qs = Order.objects.filter(
    parking_card_session__isnull=False,
    created_at__gte=start_date,
    created_at__lte=end_date,
    acquiring='tinkoff',
    terminal__isnull=False
).values(
    'parking_card_session__parking_id'
).annotate(
    total_sum=Sum('sum'),
    total_count=Count('id')
).order_by('-total_sum')

for row in qs:
    parking_id = row['parking_card_session__parking_id']
    total_sum = row['total_sum']
    total_count = row['total_count']

    try:
        rps_parking = RpsParking.objects.select_related(
            'parking__owner', 'parking__company'
        ).get(parking_id=parking_id)
        parking = rps_parking.parking
        owner = parking.owner
        company = parking.company

        owner_email = owner.email if owner and owner.email else 'Email отсутствует'
        company_email = company.email if company and company.email else 'Email отсутствует'

        owner_info = f"{owner.id} | {owner.name} | {owner_email}" if owner else "Нет владельца"
        company_info = f"{company.id} | {company.name} | {company_email}" if company else "Нет компании"

        print(f"✅ OWNER: {owner_info}")
        print(f"   COMPANY: {company_info}")
        print(f"   Parking: {parking.id} | {parking.name}")
        print(f"   Orders count: {total_count}")
        print(f"   Total sum: {total_sum}")

    except RpsParking.DoesNotExist:
        print(f"⚠️ WARNING: No RpsParking for parking_id={parking_id}")
