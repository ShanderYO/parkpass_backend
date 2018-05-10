import hashlib
import hmac
import json

from django.test import TestCase

import datetime
from django.test import TestCase
from django.test import Client

# Create your tests here.
from accounts.models import Account
from base.exceptions import ValidationException
from parkings.models import Vendor, Parking
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


    def test_rps_update_valid_body(self):
        url = '/parking/rps/session/list/update/'
        body = json.dumps({
            "parking_id":1,
            "sessions":[
                {
                    "client_id":1,
                    "started_at":1,
                    "debt":1.903,
                    "updated_at":1
                }
            ]
        })
        response = self._make_signed_json_post(url, body)
        self.assertEqual(response.status_code, 202)