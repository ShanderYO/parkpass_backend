import datetime
import hashlib
import hmac
import json
from random import randint

from django.test import Client
from django.test import TestCase

from accounts.models import Account, AccountSession, AccountTypes
from accounts.tests import create_account
from base.exceptions import ValidationException
from parkings.models import Parking, ParkingSession


class VendorFixture:
    def __init__(self, first_name="Fname", phone="89991234567", email="e@mail.com",
                 account_type=AccountTypes.VENDOR, ven_name="vendor-1", ven_secret="1234567"):
        self.vendor = Account.objects.create(
            first_name=first_name,
            phone=phone,
            email=email,
            account_type=account_type,
            ven_name=ven_name,
            ven_secret=ven_secret
        )
        self.vendor.save(not_generate_secret=True)
        self.ven_name = ven_name
        self.ven_secret = ven_secret
        self.client = Client()

    def make_signed_json_post(self, url, body):
        signature = hmac.new(self.ven_secret, body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': self.ven_name})
        return response
        

class UpdateParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/update/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()
        self.not_vendor = VendorFixture(
            email="e@e.com",
            phone="12345678900",
            account_type=AccountTypes.USER,
            ven_name="vendor-2",
            ven_secret="12321321"
        )

        Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None
        )
        Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )
        self.client = Client()

    def test_update_empty_body(self):
        url = '/api/v1/parking/update/'
        body = json.dumps({
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Not set up free_places
        body = json.dumps({
            "parking_id":1
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set parking_id negative sign
        body = json.dumps({
            "parking_id": "-12",
            "free_places": 12
        })
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set free_places not int
        body = json.dumps({
            "parking_id": 1,
            "free_places": "more"
        })

        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)

        error_code = json.loads(response.content)["code"]
        self.assertEqual(error_code, ValidationException.VALIDATION_ERROR)
        print response.content

        # Set free_places negative sign
        body = json.dumps({
            "parking_id": 1,
            "free_places": "-1"
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        print response.content
        self.assertEqual(response.status_code, 200)

    def test_update_unprivileged(self):
        url = '/api/v1/parking/update/'

        # Set up not existing parking_id
        body = json.dumps({
            "parking_id": 1,
            "free_places": 10
        })
        response = self.not_vendor.make_signed_json_post(url, body)
        print response.content
        self.assertEqual(response.status_code, 400)


class CreateSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/create/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
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

        self.client = Client()


    def test_empty_body(self):
        url = '/api/v1/parking/session/create/'
        body = json.dumps({
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
            "client_id": 25,
            "started_at": 1000000
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 200)


class UpdateSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/update/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
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

    def test_empty_body(self):
        url = '/api/v1/parking/session/update/'

        # Set up empty body
        body = json.dumps({
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 400)
        # VAlidation error
        print response.content


class CompleteSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/complete/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 200)
        print response.content


class UpdateListSessionParkingTestCase(TestCase):
    """
        Test for /api/v1/parking/session/list/update/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()

        Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
        )

        Parking.objects.create(
            name="parking-2",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=None
        )

        self.client = Client()

    def test_empty_body(self):
        url = '/api/v1/parking/session/list/update/'

        # Set up empty body
        body = json.dumps({
        })
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
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
        response = self.vendor.make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 202)
        print response.content


class ComplainTestCase(TestCase):
    """
        Test for /parking/complain/ API
    """
    def setUp(self):
        self.vendor = VendorFixture()

        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
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
        url = '/parking/complain/'
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
        url = '/parking/complain/'
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


class StatisticsTestCase(TestCase):
    def setUp(self):
        self.vendor = VendorFixture(ven_name="ven", ven_secret="Victorias")
        parking_1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=self.vendor.vendor
        )
        parking_2 = Parking.objects.create(
            name="parking-2",
            description="second",
            latitude=2,
            longitude=3,
            free_places=9,
            vendor=self.vendor.vendor
        )

        account, acc_session = create_account()

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
        pass

    def test_summary_stats(self):
        url = '/api/v1/parking/stats/summary/'

        body = json.dumps({
            'start': 0,
            'end': 120,
            'ids': '1, 2, 3, 4, 5',
        })

        response = self.vendor.make_signed_json_post(url, body)

        print response.content

        self.assertEqual(200, response.status_code)

    def test_parking_stats(self):
        url = '/api/v1/parking/stats/parking/'

        body = json.dumps({
            'start': 10,
            'end': 80,
            'pk': 1,
        })

        response = self.vendor.make_signed_json_post(url, body)

        print response.content
        result = json.loads(response.content)['sessions']
        self.assertEqual(len(result), 10)
        starts = []
        for i in result:
            starts.append(i['started_at'])
        self.assertFalse('90' in starts)

    def test_without_time(self):
        url = '/api/v1/parking/stats/parking/'

        body = json.dumps({
            'pk': 1,
        })

        response = self.vendor.make_signed_json_post(url, body)

        self.assertEqual(200, response.status_code)
