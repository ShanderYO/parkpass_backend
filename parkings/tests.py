import datetime
import hashlib
import hmac
import json

from django.test import Client
from django.test import TestCase

from accounts.models import Account, AccountSession
from base.exceptions import ValidationException
from parkings.models import Vendor, Parking, ParkingSession


class UpdateParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/update/ API
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
            vendor=vendor,
            approved=True
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None,
            approved=True
        )
        Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )
        self.client = Client()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_update_empty_body(self):
        url = '/api/v1/parking/update/'
        body = json.dumps({
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_update_incomplete_body(self):
        url = '/api/v1/parking/update/'

        # Not set up parking_id
        body = json.dumps({
            "free_places": "dimas@carabas.com"
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Not set up free_places
        body = json.dumps({
            "parking_id":1
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_update_invalid_body(self):
        url = '/api/v1/parking/update/'

        # Set parking_id not int
        body = json.dumps({
            "parking_id": "wrong_id",
            "free_places": 12
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set parking_id negative sign
        body = json.dumps({
            "parking_id": "-12",
            "free_places": 12
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set free_places not int
        body = json.dumps({
            "parking_id": 1,
            "free_places": "more"
        })

        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set free_places negative sign
        body = json.dumps({
            "parking_id": 1,
            "free_places": "-1"
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


    def test_update_undefined_parking(self):
        url = '/api/v1/parking/update/'

        # Set up not existing parking_id
        body = json.dumps({
            "parking_id": 3,
            "free_places": 10
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content


    def test_update_forbidden_parking(self):
        url = '/api/v1/parking/update/'

        # Set up not existing parking_id
        body = json.dumps({
            "parking_id": 2,
            "free_places": 10
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content


    def test_update_valid(self):
        url = '/api/v1/parking/update/'

        # Set up not existing parking_id
        body = json.dumps({
            "parking_id": 1,
            "free_places": 10
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 200)
        print response.content


class CreateSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/create/ API
    """
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor,
            approved=True
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None,
            approved=True
        )
        account = Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        ParkingSession.objects.create(
            session_id="exist-session-id",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now()
        )

        self.client = Client()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_empty_body(self):
        url = '/api/v1/parking/session/create/'
        body = json.dumps({
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_incomplete_body(self):
        url = '/api/v1/parking/session/create/'

        # Not set up started_at
        body = json.dumps({
            "session_id": "session1",
            "parking_id":1,
            "client_id":1
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Not set up session_id
        body = json.dumps({
            "parking_id": 1,
            "client_id": 1,
            "started_at":10000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_invalid_session_id(self):
        url = '/api/v1/parking/session/create/'

        # Set up session_id more 128 symbols
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0,129)]),
            "parking_id": 1,
            "client_id": 1,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_invalid_client_id(self):
        url = '/api/v1/parking/session/create/'

        # Set up not existing client_id
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0,128)]),
            "parking_id": 1,
            "client_id": 2,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content

    def test_invalid_parking_id(self):
        url = '/api/v1/parking/session/create/'

        # Set up not existing parking_id
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0, 128)]),
            "parking_id": 3,
            "client_id": 1,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content

    def test_forbidden_parking(self):
        url = '/api/v1/parking/session/create/'

        # Set up foreign parking_id
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0, 128)]),
            "parking_id": 2,
            "client_id": 1,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content

    def test_already_exist_session_id(self):
        url = '/api/v1/parking/session/create/'

        # Set up session_id is exist-session-id
        body = json.dumps({
            "session_id": "exist-session-id",
            "parking_id": 1,
            "client_id": 1,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_create_session_valid(self):
        url = '/api/v1/parking/session/create/'

        # Set up session_id new value
        body = json.dumps({
            "session_id": "valid-session-id",
            "parking_id": 1,
            "client_id": 1,
            "started_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 200)


class UpdateSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/update/ API
    """
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None
        )
        account = Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        ParkingSession.objects.create(
            session_id="exist-session-id",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_COMPLETED,
            started_at=datetime.datetime.now()
        )

        ParkingSession.objects.create(
            session_id="exist-session-id-completed",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_COMPLETED,
            started_at=datetime.datetime.now()
        )

        self.client = Client()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response


    def test_empty_body(self):
        url = '/api/v1/parking/session/update/'

        # Set up empty body
        body = json.dumps({
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


    def test_invalid_session_id(self):
        url = '/api/v1/parking/session/update/'

        # Set up session_id more 128 symbols
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0, 129)]),
            "parking_id": 1,
            "debt": 2,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


    def test_invalid_debt_negative_value(self):
        url = '/api/v1/parking/session/update/'

        # Set up debt negative sign
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0, 128)]),
            "parking_id": 1,
            "debt": "-2",
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


    def test_invalid_debt_string_value(self):
        url = '/api/v1/parking/session/update/'

        # Set up debt string
        body = json.dumps({
            "session_id": "".join(["x" for x in range(0, 128)]),
            "parking_id": 1,
            "debt": "test-string",
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


    def test_not_existing_session_id(self):
        url = '/api/v1/parking/session/update/'

        # Set up not existing session_id
        body = json.dumps({
            "session_id": "not-existing-id",
            "parking_id": 1,
            "debt": 100,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content


    def test_not_existing_parking_id(self):
        url = '/api/v1/parking/session/update/'

        # Set up not existing parking_id
        body = json.dumps({
            "session_id": "not-existing-id",
            "parking_id": 3,
            "debt": 100,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content


    def test_not_forbidden_parking_id(self):
        url = '/api/v1/parking/session/update/'

        # Set up not forbidden parking_id
        body = json.dumps({
            "session_id": "not-existing-id",
            "parking_id": 2,
            "debt": 100,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content

    def test_update_already_completed(self):
        url = '/api/v1/parking/session/update/'

        # Set up not completed session_id
        body = json.dumps({
            "session_id": "exist-session-id-completed",
            "parking_id": 1,
            "debt": 100,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        print "test_update_already_completed"
        print response.content

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)

    def test_update_session_valid(self):
        url = '/api/v1/parking/session/update/'

        # Set up not completed session_id
        body = json.dumps({
            "session_id": "exist-session-id",
            "parking_id": 1,
            "debt": 100,
            "updated_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)
        # VAlidation error
        print response.content


class CompleteSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/complete/ API
    """
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None
        )
        account = Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        ParkingSession.objects.create(
            session_id="exist-session-id",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now()
        )

        ParkingSession.objects.create(
            session_id="exist-session-id-completed",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_COMPLETED,
            started_at=datetime.datetime.now()
        )

        self.client = Client()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    # TODO add need tests

    def test_completed_session_valid(self):
        url = '/api/v1/parking/session/complete/'

        # Set up not completed session_id
        body = json.dumps({
            "session_id": "exist-session-id",
            "parking_id": 1,
            "debt": 100,
            "completed_at": 1000000
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 200)
        print response.content


class UpdateListSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/list/update/ API
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
            vendor=vendor,
            approved=True
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None,
            approved=True
        )

        self.client = Client()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_empty_body(self):
        url = '/api/v1/parking/session/list/update/'

        # Set up empty body
        body = json.dumps({
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_empty_parking_id_body(self):
        url = '/api/v1/parking/session/list/update/'
        # Not set up parking_id
        body = json.dumps({
            "sessions": [
                {
                    "session_id": "session-id-1",
                    "debt": 200,
                    "updated_at": 10000
                },
            ]
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_empty_session_body(self):
        url = '/api/v1/parking/session/list/update/'

        # Not set up sessions
        body = json.dumps({
            "parking_id": 1
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_invalid_sessions_type_body(self):
        url = '/api/v1/parking/session/list/update/'
        # Not set up sessions as string
        body = json.dumps({
            "parking_id": 1,
            "sessions": "session-string"
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_invalid_inner_sessions_type_body(self):
        url = '/api/v1/parking/session/list/update/'
        # Not set up sessions as string
        body = json.dumps({
            "parking_id": 1,
            "sessions": {
                    "session": "session-id-1",
                    "debt": 200,
                    "updated_at": 10000
                }
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def test_update_list_session_forbidden_parking(self):
        url = '/api/v1/parking/session/list/update/'

        # Set up forbidden parking_id
        body = json.dumps({
            "sessions": [
                {
                    "session_id": "session-id-1",
                    "debt": 100,
                    "updated_at": 10000
                },
                {
                    "session_id": "session-id-1",
                    "debt": 200,
                    "updated_at": 10000
                },
            ],
            "parking_id": 2,
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.RESOURCE_NOT_FOUND)
        print response.content

    def test_update_list_session_valid(self):
        url = '/api/v1/parking/session/list/update/'

        # Set up valid sessions format
        body = json.dumps({
            "sessions": [
                {
                    "session_id":"session-id-1",
                    "debt":100,
                    "updated_at":10000
                },
                {
                    "session_id":"session-id-1",
                    "debt":200,
                    "updated_at": 10000
                },
            ],
            "parking_id": 1,
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 202)
        print response.content



class ComplainTestCase(TestCase):
    """
        Test for /parking/complain/ API
    """
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking_1 = Parking.objects.create(
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

        ParkingSession.objects.create(
            session_id="exist-session-id",
            client=account,
            parking=parking_1,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now()
        )
        self.client = Client()

    def complain_invalid_session_test(self):
        url = '/api/v1/parking/complain/'
        body = json.dumps({
            "session_id": 2,
            "type": 1,
            "message": "bla-bla"
        })
        response = self.client.post(url, body,
                                    **{'HTTP_AUTHORIZATION': "Token 0ff08840935eb00fad198ef5387423bc24cd15e1"})
        self.assertEqual(response.status_code, 200)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def complain_type_session_test(self):
        url = '/parking/complain/'
        body = json.dumps({
            "session_id": 2,
            "type": 10,
            "message": "bla-bla"
        })
        response = self.client.post(url, body,
                                    **{'HTTP_AUTHORIZATION': "Token 0ff08840935eb00fad198ef5387423bc24cd15e1"})
        self.assertEqual(response.status_code, 200)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

    def complain_valid_test(self):
        url = '/api/v1/parking/complain/'
        body = json.dumps({
            "session_id":1,
            "type":1,
            "message":"bla-bla"
        })
        response = self.client.post(url, body, **{'HTTP_AUTHORIZATION': "Token 0ff08840935eb00fad198ef5387423bc24cd15e1"})
        self.assertEqual(response.status_code, 200)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content


class IssueParking(TestCase):
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_issue_parking_valid(self):
        url = '/api/v1/parking/issue/'

        body = json.dumps({
            'name': 'Worst parking ever',
            'enabled': 'False',
            'description': "We'll steal your car",
            'latitude': '55.7517462',
            'longitude': '37.6148268',
            'max_client_debt': '500',
            'address': 'Moscow, Sharikopodshipnikovskaya st., 228',
            'free_places': '80'
        })

        response = self._make_signed_json_post(url, body)
        print response.content
        self.assertEqual(response.status_code, 200)


class VendorPermissions(TestCase):
    def setUp(self):
        self.vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678",
        )
        self.vendor.save(not_generate_secret=True)
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor,
            approved=True
        )

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_normal_state(self):
        self.vendor.account_state = Vendor.ACCOUNT_STATE.NORMAL
        self.vendor.save()
        url = '/api/v1/parking/update/'
        body = json.dumps({
            'parking_id': 2,
            'free_places': 3
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(200, response.status_code)

    def test_disabled_state(self):
        self.vendor.account_state = Vendor.ACCOUNT_STATE.DISABLED
        self.vendor.save()
        url = '/api/v1/parking/update/'
        body = json.dumps({
            'parking_id': 2,
            'free_places': 3
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(400, response.status_code)
        body = json.dumps({
            'parking_id': 1,
            'free_places': 3
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(400, response.status_code)

    def test_test_state(self):
        self.vendor.account_state = 2
        self.vendor.save()
        url = '/api/v1/parking/update/'
        body = json.dumps({
            'parking_id': 2,
            'free_places': 3
        })
        response = self._make_signed_json_post(url, body)
        print response.content, response.status_code
        self.assertEqual(400, response.status_code)
        body = json.dumps({
            'parking_id': 1,
            'free_places': 3
        })
        response = self._make_signed_json_post(url, body)
        print response.content, response.status_code
        self.assertEqual(200, response.status_code)
