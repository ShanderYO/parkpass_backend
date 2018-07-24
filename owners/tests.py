import json

from django.test import Client
from django.test import TestCase

from .models import *

URL_PREFIX = "/api/v1/owner/"
TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Owner 0ff08840935eb00fad198ef5387423bc24cd15e1'}
TOKEN = "0ff08840935eb00fad198ef5387423bc24cd15e1"
LOGIN, PASSWORD = "owner123", "qwerty"
PHONE = "+7(999)1234567"
EMAIL = "test@testing.com"


def create_account(id=1, fname="Fname", phone=PHONE, email=EMAIL, password=PASSWORD, login=LOGIN):
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

        print response.content, "!!!"
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


class Password(TestCase):
    """
    This test case if for testing /login/restore and /login/changepw
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
        url = URL_PREFIX + "login/restore"

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
        url = URL_PREFIX + "login/restore"

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
        url = URL_PREFIX + "login/changepw/"

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
        url = URL_PREFIX + "login/changepw/"

        body = json.dumps({
            "old": PASSWORD,
            "new": "uiop"
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **TOKEN_DICT)

        print response.content
        self.assertEqual(response.status_code, 200)
