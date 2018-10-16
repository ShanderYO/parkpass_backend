import datetime
import hashlib
import hmac
import json
from random import randint

from django.test import Client
from django.test import TestCase

from accounts.tests import create_account as create_user_account
from parkings.models import ParkingSession, Parking
from .models import *

URL_PREFIX = "/api/v1/vendor/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Vendor ff08840935eb00fad198ef5387423bc24cd15e1'}
TOKEN = "ff08840935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "vendor", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"
SECRET = "secret"


def create_account(display_id=1, fname="Fname", phone=PHONE, email=EMAIL, password=PASSWORD,
                   ven_name=LOGIN):
    account = Vendor.objects.create(
        # id=id,
        display_id=display_id,
        first_name=fname,
        phone=phone,
        email=email,
        name=ven_name,
    )
    account.set_password(password)
    account_session = VendorSession(
        token=TOKEN,
        vendor=account
    )
    account_session.set_expire_date()
    account_session.save(not_generate_token=True)
    account.save()
    secret = str(account.secret)

    def make_signed_json_post(url, body):
        signature = hmac.new(secret, body, hashlib.sha512)
        response = Client().post(url, body, content_type="application/json",
                                 **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                    'HTTP_X_VENDOR_NAME': ven_name})
        return response

    return account, account_session, make_signed_json_post


class Authorization(TestCase):
    def setUp(self):
        self.account, self.account_session, self.sign = create_account()

    def test_login_by_name(self):
        url = URL_PREFIX + "login/"

        body = json.dumps({
            'login': LOGIN,
            'password': PASSWORD
        })

        response = Client().post(url, body, content_type="application/json")

        print response.content
        self.assertEqual(200, response.status_code)

    def test_login_by_phone(self):
        url = URL_PREFIX + "login/phone/"

        body = json.dumps({
            'phone': PHONE,
            'password': PASSWORD
        })

        response = Client().post(url, body, content_type="application/json")

        print response.content
        self.assertEqual(200, response.status_code)

    def test_login_by_email(self):
        url = URL_PREFIX + "login/email/"

        body = json.dumps({
            'email': EMAIL,
            'password': PASSWORD
        })

        response = Client().post(url, body, content_type="application/json")

        print response.content
        self.assertEqual(200, response.status_code)

    def test_get_info(self):
        url = URL_PREFIX + "info/"

        response = Client().get(url, **TOKEN_DICT)
        print response.content

        self.assertEqual(200, response.status_code)

    def test_issue_upgrade(self):
        url = URL_PREFIX + "upgradeissues/send/"

        body = json.dumps({
            'description': 'Please install Quake III Arena to parking reader',
            'issue_type': '0'
        })

        response = Client().post(url, body, content_type='application/json', **TOKEN_DICT)

        self.assertEqual(200, response.status_code)

    def test_get_top_parkings(self):
        url = URL_PREFIX + 'stats/top/'

        response = Client().post(url, '{}', content_type='application/json', **TOKEN_DICT)
        self.assertEqual(200, response.status_code)


class Password(TestCase):
    """
    This test case if for testing /login/restore and /login/changepw
    (Restoring a password by e-mail and changing it manually)
    """

    def setUp(self):
        self.account, self.account_session, self.sign = create_account()

        self.client = Client()

    def test_invalid_email_restore(self):
        """
        Testing case when invalid email is entered when attempting to restore password
        :return:
        """
        url = URL_PREFIX + "password/restore/"

        body = json.dumps({
            "email": "abra@cadabra.boom"
        })
        response = self.client.post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_email_restore(self):
        """
        Testing case when valid email is entered when attempting to restore password
        """
        url = URL_PREFIX + "password/restore/"

        body = json.dumps({
            "email": EMAIL
        })
        response = self.client.post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        print response.content

    def test_invalid_old_change(self):
        """
        Testing case when old password is invalid
        """
        url = URL_PREFIX + "password/change/"

        body = json.dumps({
            "old": "abracadabra",
            "new": "12345"
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_password_change(self):
        """
        Testing case when valid old pw entered when changing pw
        """
        url = URL_PREFIX + "password/change/"

        body = json.dumps({
            "old": PASSWORD,
            "new": "uiop"
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **TOKEN_DICT)

        print response.content
        self.assertEqual(response.status_code, 200)


class Statistics(TestCase):
    def setUp(self):
        self.account, self.account_session, self.sign = create_account()
        account, accsession = create_user_account()
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            max_places=5,
            vendor=self.account
        )
        parking_2 = Parking.objects.create(
            name="parking-2",
            description="second",
            latitude=2,
            longitude=3,
            max_places=9,
            vendor=self.account
        )
        for i in range(0, 100, 1):
            ps = ParkingSession.objects.create(
                session_id="exist-session-id%d" % i,
                client=account,
                parking=parking_1,
                state=ParkingSession.STATE_COMPLETED,
                started_at=datetime.datetime.fromtimestamp(i),
                completed_at=datetime.datetime.fromtimestamp(i + randint(10, 100)),
                debt=(randint(100, 2000))
            )
            ps.save()

    def test_summary_stats(self):
        url = URL_PREFIX + 'stats/summary/'

        body = json.dumps({
            'start': 0,
            'end': 120,
            'ids': '1, 2, 3, 4, 5',
        })

        response = Client().post(url, body, content_type='application/json',
                                 **TOKEN_DICT)

        print response.content

        self.assertEqual(200, response.status_code)

    def test_parking_stats(self):
        url = URL_PREFIX + 'stats/parking/'

        body = json.dumps({
            'start': 20,
            'end': 80,
            'pk': 2,
        })

        response = Client().post(url, body, content_type='application/json',
                                 **TOKEN_DICT)

        print response.content
        result = json.loads(response.content)['sessions']
        self.assertEqual(len(result), 10)
        starts = []
        for i in result:
            starts.append(i['started_at'])
        self.assertFalse('90' in starts)

    def test_without_time(self):
        url = URL_PREFIX + 'stats/parking/'

        body = json.dumps({
            'pk': 1,
        })

        response = Client().post(url, body, content_type='application/json',
                                 **TOKEN_DICT)

        self.assertEqual(200, response.status_code)


class TestMethods(TestCase):

    def setUp(self):
        self.account, self.account_session, self.sign = create_account()

    def test_created_without_session(self):
        url = URL_PREFIX + 'test/'
        response = Client().post(url, '{}', content_type='application/json',
                                 **TOKEN_DICT)
        self.assertEqual(400, response.status_code)

    def test_created_with_session(self):
        url = URL_PREFIX + 'test/'

        session = ParkingSession(
            started_at=datetime.datetime.now(),
            client=self.account.test_user,
            parking=self.account.test_parking,
            state=3
        )
        session.save()

        response = Client().post(url, '{}', content_type='application/json',
                                 **TOKEN_DICT)

        print response.content
        self.assertEqual(200, response.status_code)
