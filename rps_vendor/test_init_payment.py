# rps_vendor/test_init_payment.py

import pytest
import uuid
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Account, AccountSession
from parkings.models import Parking
from rps_vendor.models import RpsParking, ParkingCard, RpsParkingCardSession
from owners.models import Company, Owner


@pytest.fixture
def account():
    account = Account(first_name="Test", phone="+79991234567", email="test@testing.com")
    account.set_password("qwerty")
    account.save()
    session = AccountSession(token="tok", account=account)
    session.set_expire_date()
    session.save(not_generate_token=True)
    return account


@pytest.fixture
def owner():
    return Owner.objects.create(
        name="Test Owner", phone="+71234567890", email="owner@example.com"
    )


@pytest.fixture
def company(owner):
    return Company.objects.create(
        owner=owner,
        name="Test Company",
        legal_address="Test Legal Address",
        actual_address="Test Actual Address",
    )


@pytest.fixture
def parking(company):
    return Parking.objects.create(
        name="Test Parking",
        address="Test Address",
        company=company,
        owner=company.owner,
        latitude=55.7558,
        longitude=37.6173,
        domain="test.local",
        currency="UZS",
        tz_name="Asia/Tashkent",
        acquiring="uzumbank",
        rps_parking_card_available=True,
    )


@pytest.fixture
def parking_card(account, parking):
    card = ParkingCard.objects.create(card_id="TESTCARD123", phone=account.phone)

    RpsParkingCardSession.objects.create(
        parking_card=card,
        parking_id=parking.id,
        debt=100,
        duration=3600,
        account=account,
        state=1,
        from_datetime=timezone.now() - timedelta(minutes=60),
        leave_at=timezone.now() + timedelta(minutes=60),
        created_at=timezone.now() - timedelta(minutes=60),
        client_uuid=uuid.uuid4(),
    )

    return card


@pytest.fixture
def rps_parking(parking):
    return RpsParking.objects.create(
        parking=parking,
        integrator_id="dummy-id",
        integrator_password="secret",
        token="dummy-token",
    )


@pytest.mark.django_db
def test_init_payment_uzumbank(parking, rps_parking, account, parking_card):
    client = APIClient()

    url = reverse("init_payment")
    payload = {
        "card_id": parking_card.card_id,
        "parking_id": parking.id,
        "duration": 60,
        "currency": "UZS",
        "parking_enter_time": (timezone.now() - timedelta(minutes=30)).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        ),
        "parking_amount_calculated_time": (
            timezone.now() - timedelta(minutes=25)
        ).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "parking_redirect_url": "https://example.com/success/",
        "parking_payment_url": "https://example.com/pay/",
        "amount": 1500,
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == 200, response.content
