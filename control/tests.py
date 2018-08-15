import json

from django.test import Client
from django.test import TestCase
from dss.Serializer import serializer

from parkings.models import Parking
from parkings.tests import _create_parking, _create_vendor
from .models import *

URL_PREFIX = "/api/v1/control/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Admin ff08840935eb00fad198ef5387423bc24cd15e1'}
TOKEN = "ff08840935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "adminadmin", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"


def create_account(fname="Fname", phone=PHONE, email=EMAIL, password=PASSWORD,
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

        # print response.content
        self.assertEqual(200, response.status_code)


class ParkingEdit(TestCase):
    def setUp(self):
        self.account, self.account_session = create_account()
        _create_parking(_create_vendor())

    def test_show_parking(self):
        url = URL_PREFIX + "objects/parking/1/"

        response = Client().post(url, '{}', content_type="application/json", **TOKEN_DICT)
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

        response = Client().post(url, body, content_type="application/json", **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(200, response.status_code)
        self.assertEqual(json.loads("""{
  "description": "My test parking", 
  "name": "NameParking", 
  "created_at": 1534291200.0, 
  "vendor_id": 1, 
  "enabled": true, 
  "longitude": 2.0, 
  "id": 1, 
  "free_places": 3, 
  "address": "addr", 
  "latitude": 2.0, 
  "max_client_debt": 50, 
  "approved": false, 
  "owner_id": null
}"""), serializer(Parking.objects.get(id=1)))

    def test_invalid_changes(self):
        url = URL_PREFIX + "objects/parking/1/"

        body = json.dumps({
            "approved": 'yeah, sure',
        })

        response = Client().post(url, body, content_type="application/json", **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(400, response.status_code)
        self.assertEqual('ValidationException', j['exception'])

    def test_delete(self):
        url = URL_PREFIX + "objects/parking/1/"

        body = json.dumps({
            "delete": 'true',
        })

        response = Client().post(url, body, content_type="application/json", **TOKEN_DICT)
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

        response = Client().post(url, body, content_type="application/json", **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(400, response.status_code)
