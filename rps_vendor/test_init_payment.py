import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APIClient

from owners.models import Owner, Company
from accounts.models import Account, AccountSession
from parkings.models import Parking
from rps_vendor.models import ParkingCard, RpsParking, RpsParkingCardSession


@pytest.fixture
def account():
    account = Account(
        first_name="Test", phone="+7(999)1234567", email="test@testing.com"
    )
    account.set_password("qwerty")
    account.save()
    session = AccountSession(token="tok", account=account)
    session.set_expire_date()
    session.save(not_generate_token=True)
    return account


@pytest.mark.django_db
def test_init_payment_uzumbank(account):
    # Клиент API
    client = APIClient()

    # Создание владельца, компании и парковки
    owner = Owner.objects.create(
        name="Test Owner", phone="+71234567890", email="owner@example.com"
    )
    company = Company.objects.create(
        owner=owner,
        name="Test Company",
        legal_address="Test Legal Address",
        actual_address="Test Actual Address",
    )
    parking = Parking.objects.create(
        name="Test Parking",
        address="Test Address",
        company=company,
        owner=owner,
        latitude=55.7558,
        longitude=37.6173,
        domain="test.local",
        currency="UZS",
        acquiring="uzumbank",
        tz_name="Asia/Tashkent",
    )

    # Карта и сессия карты
    card_id = "TESTCARD123"
    card = ParkingCard.objects.create(card_id=card_id, phone=account.phone)

    now = datetime(2025, 7, 31, 10, 0, 0)
    RpsParkingCardSession.objects.create(
        parking_card=card,
        parking_id=parking.id,
        debt=1500,
        duration=60,
        account=account,
        state=1,
        client_uuid=uuid.uuid4(),
        from_datetime=now,
        leave_at=now + timedelta(minutes=60),
        created_at=now,
    )

    # RpsParking
    RpsParking.objects.create(parking=parking, token="dummy-token")

    # Запрос на оплату
    payload = {
        "card_id": card_id,
        "parking_id": parking.id,
        "duration": 60,
        "currency": "UZS",
        "parking_enter_time": now.strftime("%Y-%m-%d %H:%M:%S.000000"),
        "parking_amount_calculated_time": (now + timedelta(minutes=5)).strftime(
            "%Y-%m-%d %H:%M:%S.000000"
        ),
        "parking_redirect_url": "https://example.com/success/",
        "parking_payment_url": "https://example.com/pay/",
        "amount": 1500,
    }

    url = reverse("init_payment")
    response = client.post(url, data=payload, format="json")

    assert response.status_code == 200
    data = response.json()
    assert "payment_url" in data
    assert "order_id" in data
