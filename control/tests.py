import json

from django.test import Client
from django.test import TestCase

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
