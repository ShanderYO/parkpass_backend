import hashlib
import hmac
import json
import time

from django.test import TestCase

import datetime
from django.test import TestCase
from django.test import Client

# Create your tests here.
from accounts.models import Account
from parkings.models import Vendor, Parking, ParkingSession
from rps_vendor.models import RpsParking


class UpdateParkingTestCase(TestCase):
    """
        Test for /parking/v1/update/ API
    """
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor
        )

        RpsParking.objects.create(
            parking=parking1
        )

        account = Account.objects.create(
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        session = ParkingSession.objects.create(
            session_id="100000000000000001&1",
            parking=parking1,
            client=account,
            debt=190,
            state = ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            completed_at=datetime.datetime.now()
        )
        session.add_vendor_start_mark()
        session.add_vendor_complete_mark()
        session.save()

        session2 = ParkingSession.objects.create(
            session_id="100000000000000001&2",
            parking=parking1,
            client=account,
            debt=190,
            state=ParkingSession.STATE_STARTED,
            started_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            completed_at=datetime.datetime.now()
        )
        session2.add_vendor_start_mark()
        session2.save()

        self.client = Client()


    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678", body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response


    def test_rps_update_closed_session(self):
        url = '/parking/rps/session/list/update/'
        body = json.dumps({
            "parking_id": 1,
            "sessions": [
                {
                    "client_id": 100000000000000001,
                    "started_at": 2,
                    "debt": 1.903,
                    "updated_at": 1
                }
            ]
        })
        response = self._make_signed_json_post(url, body)
        print response
        time.sleep(10)
        self.assertEqual(response.status_code, 202)

    def test_rps_update_valid_body(self):
        url = '/parking/rps/session/list/update/'
        body = json.dumps({
            "parking_id":1,
            "sessions":[
                {
                    "client_id":100000000000000001,
                    "started_at":1,
                    "debt":1.903,
                    "updated_at":1
                }
            ]
        })
        response = self._make_signed_json_post(url, body)
        print response
        time.sleep(10)
        self.assertEqual(response.status_code, 202)