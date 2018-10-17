# -!- coding: utf-8 -!-
import datetime
import json
from random import randint

from django.test import Client
from django.test import TestCase

from accounts.tests import create_account as create_user_account
from base.utils import clear_phone
from parkings.models import ParkingSession, Parking
from vendors.tests import create_account as create_vendor_account
from .models import *

URL_PREFIX = "/api/v1/owner/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Owner 2ff08840935eb00fad198ef5387423bc24cd15e1'}
TOKEN = "2ff08840935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "owner123", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"


def create_account(id=1, fname="Fname", phone=clear_phone(PHONE), email=EMAIL, password=PASSWORD, login=LOGIN):
    account = Owner.objects.create(
        # id=id,
        first_name=fname,
        phone=phone,
        email=email,
        name=login
    )
    account.set_password(password)
    account_session = OwnerSession(
        token=TOKEN,
        owner=account
    )
    account_session.set_expire_date()
    account_session.save(not_generate_token=True)
    account.save()

    return account, account_session


class Authorization(TestCase):
    def setUp(self):
        self.account, self.account_session = create_account()

    def test_login_by_name(self):
        url = URL_PREFIX + "login/"

        body = json.dumps({
            'login': LOGIN,
            'password': PASSWORD
        })

        response = Client().post(url, body, content_type="application/json")

        # print response.content
        self.assertEqual(200, response.status_code)

    def test_login_by_phone(self):
        url = URL_PREFIX + "login/phone/"

        body = json.dumps({
            'phone': PHONE,
            'password': PASSWORD
        })

        response = Client().post(url, body, content_type="application/json")

        # print response.content
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

    def test_account_info(self):
        url = URL_PREFIX + "stats/info/"

        response = Client().get(url, **TOKEN_DICT)

        print json.dumps(json.loads(response.content), indent=4), 111


class Password(TestCase):
    """
    This test case is for testing /login/restore and /login/changepw
    (Restoring a password by e-mail and changing it manually)
    """

    def setUp(self):
        self.account, self.account_session = create_account()

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
        self.account, self.account_session, self.sign = create_vendor_account()
        account, accsession = create_user_account()
        self.owneracc, self.owneraccsess = create_account()
        company = Company.objects.create(
            owner=self.owneracc,
            name="Test company",
            inn="1234567890",
            kpp="123456789012",
            legal_address="ewsfrdg",
            actual_address="sadfbg",
            email=EMAIL,
            phone=PHONE,
            checking_account="1234",
            checking_kpp="123456789012"
        )
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            max_places=5,
            vendor=self.account,
            company=company
        )
        parking_2 = Parking.objects.create(
            name="parking-2",
            description="second",
            latitude=2,
            longitude=3,
            max_places=9,
            vendor=self.account,
            company=company
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

    def test_parking_stats_single(self):
        url = URL_PREFIX + 'stats/sessions/'

        body = json.dumps({
            'start': 20,
            'end': 80,
            'pk': 2,
        })

        response = Client().post(url, body, content_type='application/json',
                                 **TOKEN_DICT)

        # print response.content, 'single'
        self.assertEqual(200, response.status_code)

    def test_parking_stats_all(self):
        url = URL_PREFIX + 'stats/sessions/'

        body = json.dumps({
            'start': 20,
            'end': 80,
        })

        response = Client().post(url, body, content_type='application/json',
                                 **TOKEN_DICT)

        # print response.content, 'all'
        self.assertEqual(200, response.status_code)


class Companies(TestCase):
    def setUp(self):
        self.owneracc, self.owneraccsess = create_account()
        self.url = URL_PREFIX + 'company/'
        Company.objects.create(
            name='Foobar company',
            kpp='12345678',
            inn='12345432',
            legal_address='erfgef',
            actual_address='ewrgfbgn',
            checking_account='12343223423432',
            checking_kpp='1234532',
            email='foobar@gmail.com',
            phone='+2(121)2121212',
            owner=self.owneracc
        )

    def test_show(self):
        url = self.url + '1/'
        body = '{}'
        response = Client().post(url, body, content_type='application/json', **TOKEN_DICT)
        # print response.content, 12321
        # print json.dumps(json.loads(response.content), indent=4), 111
        self.assertEqual(200, response.status_code)

    def test_paginate(self):
        url = self.url + 'view/1/'
        body = '{}'
        response = Client().post(url, body, content_type='application/json', **TOKEN_DICT)
        # print json.dumps(json.loads(response.content), indent=4), 12321
        self.assertEqual(200, response.status_code)


class Issue(TestCase):

    def test_full_data(self):
        url = URL_PREFIX + 'issue/'

        body = json.dumps({
            'name': 'PashaWNN',
            'phone': '81234567890',
            'email': 'wnnpasha@mailg.moc'
        })

        response = Client().post(url, body, content_type='application/json')
        print response.content
        self.assertEqual(200, response.status_code)

    def test_partial_data(self):
        url = URL_PREFIX + 'issue/'

        body = json.dumps({
            'name': 'PashaWNN',
            'phone': '81234567890',
        })

        response = Client().post(url, body, content_type='application/json')
        print response.content
        self.assertEqual(200, response.status_code)

        url = URL_PREFIX + 'issue/'

        body = json.dumps({
            'name': 'PashaWNN',
            'email': 'wnnpasha@mailg.moc'
        })

        response = Client().post(url, body, content_type='application/json')
        print response.content
        self.assertEqual(400, response.status_code)

    def test_no_name(self):
        url = URL_PREFIX + 'issue/'

        body = json.dumps({
            'phone': '81234567890',
            'email': 'wnnpasha@mailg.moc'
        })

        response = Client().post(url, body, content_type='application/json')
        print response.content
        self.assertEqual(400, response.status_code)


class Tariff(TestCase):
    def setUp(self):
        self.account, self.account_session, self.sign = create_vendor_account()
        self.owneracc, self.owneraccsess = create_account()
        company = Company.objects.create(
            owner=self.owneracc,
            name="Test company",
            inn="1234567890",
            kpp="123456789012",
            legal_address="ewsfrdg",
            actual_address="sadfbg",
            email=EMAIL,
            phone=PHONE,
            checking_account="1234",
            checking_kpp="123456789012"
        )
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            max_places=5,
            vendor=self.account,
            company=company
        )
        self.tariff = json.dumps({
            'tariff': [
                {
                    'dayList': [0, 1, 2, 3, 4],
                    'periodList': [
                        {
                            'time_start': 8 * 60 * 60,
                            'time_end': 17 * 60 * 60,
                            'description': "First 3 hrs: free\nNext: 200 rur"
                        },
                        {
                            'time_start': 17 * 60 * 60,
                            'time_end': 24 * 60 * 60,
                            'description': "First 3 hrs: free\nNext: 200 rur"
                        }
                    ]
                },
                {
                    'dayList': [5, 6],
                    'periodList': [
                        {
                            'time_start': 8 * 60 * 60,
                            'time_end': 20 * 60 * 60,
                            'description': 'First hr: free\nNext: 200 rur'
                        },
                        {
                            'time_start': 20 * 60 * 60,
                            'time_end': 24 * 60 * 60,
                            'description': 'Every hr: 300 rur'
                        }
                    ]
                }
            ]
        })

    def test_apply_new_tariff(self):
        url = URL_PREFIX + 'parking/1/tariff/'

        response = Client().post(url, self.tariff, content_type='application/json', **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)


class ConnectIssueTests(TestCase):
    def setUp(self):
        create_vendor_account()
        create_account()
        p = Parking.objects.get(id=1)
        p.enabled = True
        p.save()

    def test_exist_vendor(self):
        url = URL_PREFIX + 'connectissue/'

        body = json.dumps({
            'parking_id': 1,
            'vendor_id': 1,
            'contact_email': 'abcd@efgh.jk'
        })

        response = Client().post(url, body, content_type='application/json', **TOKEN_DICT)
        self.assertEqual(200, response.status_code)
        ConnectIssue.objects.get(id=1)

    def test_not_exist_vendor(self):
        url = URL_PREFIX + 'connectissue/'

        body = json.dumps({
            'parking_id': 1,
            'org_name': 'Organisation',
            'email': 'abdf@srvdbg.dcc',
            'website': 'werefgfb.com',
            'phone': '89994444444',
            'contact_email': 'abcd@efgh.jk',
        })

        response = Client().post(url, body, content_type='application/json', **TOKEN_DICT)
        self.assertEqual(200, response.status_code)
        ConnectIssue.objects.get(id=1)
