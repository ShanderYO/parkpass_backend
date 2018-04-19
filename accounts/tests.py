import json

from django.core.urlresolvers import reverse
from django.test import TestCase

# Create your tests here.
from accounts.models import Account, AccountSession
from base.exceptions import ValidationException, AuthException
from parkings.models import Vendor, Parking


class AccountTestCase(TestCase):
    """
        Test for /accounts/ API method request without user
    """
    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 415)
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)


    def test_empty_body_request(self):
        url = "/account/login/"

        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        error_code = json.loads(response.content)["code"]
        self.assertNotEqual(error_code, ValidationException.JSON_PARSE_ERROR)

        body = {}
        response = self.client.post(url, body, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, AuthException.NOT_FOUND_CODE)


    def test_no_json_body_request(self):
        url = "/account/login/"

        body = {
            "foo":"bar"
        }
        response = self.client.post(url, body, content_type="application/json")
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.JSON_PARSE_ERROR)


    def test_json_body_request(self):
        url = "/account/login/"

        body = json.dumps({
            "foo": "bar"
        })
        response = self.client.post(url, body, content_type="application/json")
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, AuthException.NOT_FOUND_CODE)


class LoginTestCase(TestCase):
    """
        Test for /account/login/ API method request without user
    """

    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 415)
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)


class LogoutTestCase(TestCase):
    """
        Test for /account/login/ API method request without user
    """

    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 415)
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)


class StartAccountTestCase(TestCase):
    """
        Test for /account/session/start
    """

    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
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
            id=1,
            first_name="Test1",
            phone="+7(910)8271910",
        )

        AccountSession.objects.create(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            expired_at=sd,
            account=account
        )
        self.client = Client()

    def test_second_active_session(self):
        pass

