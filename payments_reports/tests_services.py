import pytest
from datetime import date, datetime
from decimal import Decimal

from owners.models import Company, Owner
from accounts.models import Account, AccountSession
from parkings.models import Parking, ParkingSession
from payments.models import Order, TinkoffPayment, Terminal
from payments_reports.models import ParkingReportConfig
from payments_reports.services import OwnersPaymentsReports
from rps_vendor.models import RpsParking, RpsParkingCardSession, ParkingCard


@pytest.fixture
def account(
    name="Test", phone="+7(999)1234567", email="test@testing.com", password="qwerty"
):
    TOKEN = "0ff08840935eb00fad198ef5387423bc24cd15e1"
    account = Account(first_name=name, phone=phone, email=email)
    account.set_password(password)
    account.save()
    account_session = AccountSession(token=TOKEN, account=account)
    account_session.set_expire_date()
    account_session.save(not_generate_token=True)
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
        latitude=55.7558,
        longitude=37.6173,
    )


@pytest.fixture
def terminal():
    return Terminal.objects.create(
        name="Main Terminal", terminal_key="testkey", password="testpass"
    )


@pytest.fixture
def parking_session(parking, account):
    return ParkingSession.objects.create(
        session_id="sess1",
        client=account,
        parking=parking,
        state=ParkingSession.STATE_COMPLETED_FULLY,
        client_state=ParkingSession.CLIENT_STATE_COMPLETED,
        started_at=datetime(2025, 7, 10, 10, 0),
        completed_at=datetime(2025, 7, 10, 12, 0),
        duration=7200,
    )


@pytest.fixture
def parking_card(account):
    return ParkingCard.objects.create(card_id="CARD-001", phone=account.phone)


@pytest.fixture
def parking_card_session(parking, parking_card, account):
    return RpsParkingCardSession.objects.create(
        parking_card=parking_card,
        parking_id=parking.id,
        debt=100,
        duration=3600,
        account=account,
        state=1,
    )


@pytest.fixture
def parking_report_config(owner, parking):
    return ParkingReportConfig.objects.create(
        owner=owner,
        parking=parking,
        commission_percent=10,
        recipient_name="Test Recipient",
        inn="1234567890",
        kpp="123456789",
        bank_bik="044525225",
        bank_account="40817810099910004312",
        payout_periodicity="monthly",
        report_emails="owner@example.com",
    )


@pytest.fixture
def tinkoff_payment(parking_session, parking_card_session, terminal):
    order = Order.objects.create(
        sum=Decimal("100.00"),
        session=parking_session,
        parking_card_session=parking_card_session,
        terminal=terminal,
        authorized=True,
        paid=True,
        acquiring="tinkoff",
    )
    return TinkoffPayment.objects.create(order=order, status=7)


@pytest.fixture
def rps_parking(parking):
    return RpsParking.objects.create(
        parking=parking,
        integrator_id="dummy-id",
        integrator_password="secret",
        token="dummy-token",
    )


@pytest.mark.django_db
def test_generate_report_for_owner(owner, parking_report_config):
    report = OwnersPaymentsReports.generate_report_for_owner(
        owner, date(2025, 7, 1), date(2025, 7, 31)
    )
    assert report is not None
    assert report.owner == owner
    assert report.payout_amount == 0
    assert report.total_amount == 0
    assert report.total_commission == 0


@pytest.mark.django_db
def test_generate_report_with_payments(
    owner,
    parking_report_config,
    tinkoff_payment,
    rps_parking,
):
    report = OwnersPaymentsReports.generate_report_for_owner(
        owner, date(2025, 7, 1), date(2025, 7, 31)
    )
    assert report is not None
    assert report.owner == owner
    assert report.payout_amount == Decimal("90.00")
    assert report.total_amount == Decimal("100.00")
    assert report.total_commission == Decimal("10.00")
