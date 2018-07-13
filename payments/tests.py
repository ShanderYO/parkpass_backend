import json

from django.test import TestCase
from django.test import Client

from accounts.models import Account, AccountSession, AccountTypes
from parkings.models import Parking
from payments.models import Order, TinkoffPayment, PAYMENT_STATUS_NEW


class PaymentCallbackTestCase(TestCase):
    """
        Test for /api/v1/payments/callback/ API
    """
    def setUp(self):
        vendor = Account.objects.create(
            first_name="Fname",
            phone="89991234567",
            email="e@mail.com",
            account_type=AccountTypes.VENDOR,
            ven_name="vendor-1",
            ven_secret="1234567"
        )
        vendor.save(not_generate_secret=True)

        Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor
        )

        account = Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        init_order = Order.objects.create(
            id=209,
            sum=1.00,
            account=account,
        )

        TinkoffPayment.objects.create(
            payment_id=21182211,
            status=PAYMENT_STATUS_NEW,
            order=init_order,
            receipt_data=""
        )

        self.client = Client()

    def test_rejected_callback(self):
        url = '/api/v1/payments/callback/'
        body = json.dumps({
            u'OrderId': u'209',
            u'Status': u'REJECTED',
            u'Success': False,
            u'Token': u'bc9faaaf69b9c6fc63de7cfbfda96c58a0b78cbed50c3da1305f51d8736bc403',
            u'ExpDate': u'1122',
            u'ErrorCode': u'1051',
            u'Amount': 100,
            u'TerminalKey': u'1516954410942DEMO',
            u'CardId': 3585330,
            u'PaymentId': 21182211,
            u'Pan': u'500000******0009'
        })
        response = self.client.post(url, body, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        print response

    def test_confirm_callback(self):
        url = '/api/v1/payments/callback/'
        body = json.dumps({
            u'OrderId': u'209',
            u'Status': u'CONFIRMED',
            u'Success': True,
            u'Token': u'6fcb8e5e0980a5810f22845886b7d8cc06130019dbe40b2c8b2c0fd46a9d9dd5',
            u'ExpDate': u'1122',
            u'ErrorCode': u'0',
            u'Amount': 100,
            u'TerminalKey': u'1516954410942DEMO',
            u'CardId': 3585330,
            u'PaymentId': 21182211,
            u'Pan': u'430000******0777'
        })
        response = self.client.post(url, body, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        print response