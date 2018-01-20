import json

from django.core.urlresolvers import reverse
from django.test import TestCase

# Create your tests here.
from base.exceptions import ValidationException, AuthException


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
