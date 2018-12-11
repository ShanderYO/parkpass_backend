import datetime
import json
from random import randint

from django.test import Client
from django.test import TestCase

from accounts.tests import create_account as create_user_account
from base.utils import clear_phone
from parkings.models import Parking, ParkingSession, ComplainSession
from parkings.tests import _create_parking, _create_vendor
from .models import *

URL_PREFIX = "/api/v1/control/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Admin ff03440935eb00fad198ef5387423bc24cd15e1',
              'content_type': 'application/json'}
TOKEN = "ff03440935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "adminadmin", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"


def create_account(fname="Fname", phone=clear_phone(PHONE), email=EMAIL, password=PASSWORD,
                   ven_name=LOGIN):
    account = Admin.objects.create(
        first_name=fname,
        phone=phone,
        email=email,
        name=ven_name,
    )
    account.set_password(password)
    account_session = AdminSession(
        token=TOKEN,
        admin=account
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

        print response.content
        self.assertEqual(200, response.status_code)


class ParkingEdit(TestCase):
    def setUp(self):
        self.account, self.account_session = create_account()
        _create_parking(_create_vendor())

    def test_show_parking(self):
        url = URL_PREFIX + "objects/parking/1/"

        response = Client().post(url, '{}', **TOKEN_DICT)
        j = json.loads(response.content)
        # print json.dumps(j, indent=2)
        self.assertEqual(200, response.status_code)
        # self.assertEqual(j, serializer(Parking.objects.get(id=1)))

    def test_valid_changes(self):
        url = URL_PREFIX + "objects/parking/1/"

        body = json.dumps({
            "description": "My test parking",
            "name": 'NameParking',
            "created_at": 1534291200.0,
            "vendor_id": 1,
            "enabled": True,
            "longitude": 2.0,
            "free_places": 3,
            "address": 'addr',
            "latitude": 2.0,
            "max_client_debt": 50,
            "approved": 'False',
        })

        response = Client().post(url, body, **TOKEN_DICT)
        # j = json.loads(response.content)
        # print json.dumps(j, indent=2)
        self.assertEqual(200, response.status_code)

    def test_invalid_changes(self):
        url = URL_PREFIX + "objects/parking/1/"

        body = json.dumps({
            "approved": 'yeah, sure',
        })

        response = Client().post(url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertEqual('ValidationException', j['exception'])

    def test_delete(self):
        url = URL_PREFIX + "objects/parking/1/"

        body = json.dumps({
            "delete": 'true',
        })

        response = Client().post(url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual({}, j)
        with self.assertRaises(ObjectDoesNotExist):
            Parking.objects.get(id=1)

    def test_create_not_null_empty(self):
        url = URL_PREFIX + "objects/parking/create/"

        body = json.dumps({
            "description": "My test parking",
            "name": 'NameParking',
            "created_at": 1534291200.0,
            "vendor_id": 1,
            "enabled": True,
            "latitude": 2.0,
            "max_client_debt": 50,
            "approved": 'False',
        })

        response = Client().post(url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(400, response.status_code)


class ParkingSessionEdit(TestCase):
    def setUp(self):
        self.url = URL_PREFIX + "objects/parkingsession/"
        create_account()
        self.account, self.account_session = create_user_account()
        parking = _create_parking(_create_vendor())
        ParkingSession.objects.create(
            session_id="exist-session-id",
            client=self.account,
            parking=parking,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now()
        )

    def test_show_ps(self):
        url = self.url + "1/"

        response = Client().post(url, '{}', **TOKEN_DICT)
        # j = json.loads(response.content)
        # print json.dumps(j, indent=2)
        self.assertEqual(200, response.status_code)

    def test_delete_ps(self):
        url = self.url + "1/"

        body = json.dumps(
            {
                'delete': True
            })

        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(200, response.status_code)
        with self.assertRaises(ObjectDoesNotExist):
            ParkingSession.objects.get(id=1)

    def test_edit_ps(self):
        url = self.url + "1/"

        body = json.dumps({
            "parking_id": 2,
            "started_at": 1534345694.0,
            "created_at": 1534234000.0,
            "try_refund": True,
            "session_id": "exsdt-session-id",
            "updated_at": 12345,
            "completed_at": 34567,
            "state": 5,
            "current_refund_sum": 2,
            "client_id": 1,
            "target_refund_sum": 5,
            "debt": 10,
            "is_suspended": True,
            "suspended_at": "0"
        })

        response = Client().post(url, body, **TOKEN_DICT)


class VendorEdit(TestCase):
    def setUp(self):
        self.url = URL_PREFIX + "objects/vendor/"
        create_account()
        _create_vendor()

    def test_show_vendor(self):
        url = self.url + "1/"

        response = Client().post(url, '{}', **TOKEN_DICT)
        j = json.loads(response.content)

        # print json.dumps(j, indent=2)

        self.assertEqual(200, response.status_code)

    def test_edit_vendor(self):
        url = self.url + "1/"

        body = json.dumps(
            {
                "display_id": 3,
                "first_name": "Fname",
                "last_name": "Lname",
                "test_parking_id": 1,
                "name": "tst-parking-vendor",
                "phone": "1234",
                "created_at": 0534464000.0,
                "sms_code": "smsms",
                "secret": "123regr8",
                "email": "mail@mail.ur",
                "test_user_id": 1,
                "email_confirmation_id": "confirm_me",
                "password": "sttt",
                "account_state": 2,
                "comission": 0.22
            }
        )

        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(200, response.status_code)


class ComplainPagination(TestCase):
    def setUp(self):
        self.url = URL_PREFIX + "objects/complain/view/"
        account, _ = create_user_account()
        create_account()
        vendor = _create_vendor()
        session = ParkingSession.objects.create(
            session_id="exist-session-id",
            client=account,
            parking=vendor.test_parking,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now()
        )
        for i in range(1, 20):
            ComplainSession.objects.create(
                account=account,
                session=session,
                message="Abra%s" % i,
                type=1
            )

    def test_show_complains(self):
        url = self.url + "1/"

        response = Client().post(url, '{}', **TOKEN_DICT)
        j = json.loads(response.content)

        print json.dumps(j, indent=4)


class ParkingsStatistics(TestCase):
    def setUp(self):
        create_account()
        account, _ = create_user_account()
        self.url = URL_PREFIX + "statistics/parkings/"
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="second",
            latitude=2,
            longitude=3,
            max_places=9,
            vendor=None
        )
        for i in range(0, 20):
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
        url = self.url

        body = json.dumps({
            'start': 0,
            'end': 120,
            'ids': '1, 2, 3, 4, 5',
        })

        response = Client().post(url, body, **TOKEN_DICT)

        # print json.dumps(json.loads(response.content), indent=2)

        self.assertEqual(200, response.status_code)


class FilterPagination(TestCase):
    def setUp(self):
        create_account()
        account, _ = create_user_account()
        self.url = URL_PREFIX + "objects/parking/view/1/"
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="first",
            latitude=2,
            longitude=3,
            approved=True,
            max_places=9,
            vendor=None
        )
        parking_2 = Parking.objects.create(
            name="parking-2",
            description="second",
            latitude=2,
            longitude=3,
            approved=False,
            max_places=9,
            vendor=None
        )
        parking_3 = Parking.objects.create(
            name="parking-3",
            description="third",
            latitude=4,
            longitude=5,
            approved=False,
            max_places=10,
            vendor=None
        )

    def test_show_approved(self):
        body = json.dumps({
            'approved__eq': True
        })

        response = Client().post(self.url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(1, len(j['objects']))
        self.assertEqual(True, j['objects'][0]['approved'])

    def test_show_not_approved(self):
        body = json.dumps({
            'approved__ne': True
        })

        response = Client().post(self.url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(2, len(j['objects']))
        self.assertEqual(False, j['objects'][0]['approved'])

    def test_show_free(self):
        body = json.dumps({
            'free_places__gt': 0
        })

        response = Client().post(self.url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(3, len(j['objects']))

    def test_show_busy(self):
        body = json.dumps({
            'free_places': 0
        })

        response = Client().post(self.url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(0, len(j['objects']))

    def test_description_in(self):
        body = json.dumps({
            'description__in': [
                'second', 'third'
            ]
        })

        response = Client().post(self.url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(2, len(j['objects']))
