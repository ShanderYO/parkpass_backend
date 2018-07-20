import json

from django.test import Client
from django.test import TestCase

from .models import *

URL_PREFIX = "/api/v1/vendor/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'}
TOKEN = "0ff08840935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "vendor", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"
SECRET = "secret"


def create_account(id=1, fname="Fname", phone=PHONE, email=EMAIL, password=PASSWORD,
                   ven_name=LOGIN, secret=SECRET):
    account = Vendor.objects.create(
        id=id,
        first_name=fname,
        phone=phone,
        email=email,
        name=ven_name,
        secret=secret
    )
    account.set_password(password)
    account_session = VendorSession(
        token=TOKEN,
        vendor=account
    )
    account_session.set_expire_date()
    account_session.save(not_generate_token=True)
    account.save()
    return account, account_session


class Authorization(TestCase):
    def setUp(self):
        self.account, self.account_session = create_account()

    def test_login_by_name(self):
        url = "/api/v1/vendor/login/"

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
