import hashlib
import hmac
import json
import time

from django.test import Client
from django.test import TestCase

# Create your tests here.
from accounts.models import Account
from parkings.models import Vendor, Parking, ParkingSession
from rps_vendor.models import RpsParking


class UpdateSubscriptionTestCase(TestCase):
    def setUp(self):
        vendor = Vendor(
            display_id=127,
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking1 = Parking.objects.create(
            id=1,
            name="parking-1",
            description="default",
            latitude=1,
            longitude=1,
            max_places=5,
            vendor=vendor
        )

        RpsParking.objects.create(
            parking=parking1
        )

        account = Account.objects.create(
            id="100000000000000001",
            first_name="Test first_name",
            last_name="Test last_name",
            phone="+7(909)1239889",
        )

        self.client = Client()

    def tearDown(self):
        Vendor.objects.all().delete()
        Parking.objects.all().delete()
        RpsParking.objects.all().delete()
        Account.objects.all().delete()

    def _make_signed_json_post(self, url, body):
        signature = hmac.new("12345678".encode('utf-8'), body, hashlib.sha512)
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_X_SIGNATURE': signature.hexdigest(),
                                       'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
        return response

    def test_rps_update_unlimited_subscription(self):
        url = '/api/v1/parking/rps/subscription/update/'
        body = json.dumps({
            "parking_id": 1,
            "user_id": 100000000000000001,
            "unlimited": True,
            "data": "zdasdasdas"
        })
        response = self._make_signed_json_post(url, body.encode('utf-8'))
        print(response.content)
        time.sleep(10)
        self.assertEqual(response.status_code, 200)

    def test_rps_update_expiring_subscription(self):
        url = '/api/v1/parking/rps/subscription/update/'
        body = json.dumps({
            "parking_id": 1,
            "user_id": 100000000000000001,
            "data": "zdasdasdas",
            "name":  "Name",
            "description": "Desc",
            "duration": 10022,
            "id_ts": "lalka",
            "id_transition": "transition",
            "expired_at": 111
        })

        response = self._make_signed_json_post(url, body.encode('utf-8'))
        print(response.content)
        time.sleep(10)
        self.assertEqual(response.status_code, 200)

#
# class UpdateParkingTestCase(TestCase):
#     """
#         Test for /parking/v1/update/ API
#     """
#     def setUp(self):
#         vendor = Vendor(
#             display_id=127,
#             name="test-parking-vendor",
#             secret="12345678"
#         )
#         vendor.save(not_generate_secret=True)
#
#         parking1 = Parking.objects.create(
#             name="parking-1",
#             description="default",
#             latitude=1,
#             longitude=1,
#             max_places=5,
#             vendor=vendor
#         )
#
#         RpsParking.objects.create(
#             parking=parking1
#         )
#
#         account = Account.objects.create(
#             first_name="Test first_name",
#             last_name="Test last_name",
#             phone="+7(909)1239889",
#         )
#
#         session = ParkingSession.objects.create(
#             session_id="100000000000000001&1",
#             parking=parking1,
#             client=account,
#             debt=190,
#             state = ParkingSession.STATE_STARTED,
#             started_at=timezone.now(),
#             updated_at=timezone.now(),
#             completed_at=timezone.now()
#         )
#         session.add_vendor_start_mark()
#         session.add_vendor_complete_mark()
#         session.save()
#
#         session2 = ParkingSession.objects.create(
#             session_id="100000000000000001&2",
#             parking=parking1,
#             client=account,
#             debt=190,
#             state=ParkingSession.STATE_STARTED,
#             started_at=timezone.now(),
#             updated_at=timezone.now(),
#             completed_at=timezone.now()
#         )
#         session2.add_vendor_start_mark()
#         session2.save()
#
#         self.client = Client()
#
#
#     def _make_signed_json_post(self, url, body):
#         signature = hmac.new("12345678".encode('utf-8'), body, hashlib.sha512)
#         response = self.client.post(url, body, content_type="application/json",
#                                     **{'HTTP_X_SIGNATURE': signature.hexdigest(),
#                                        'HTTP_X_VENDOR_NAME': "test-parking-vendor"})
#         return response
#
#
#     def test_rps_update_closed_session(self):
#         url = '/api/v1/parking/rps/session/list/update/'
#         body = json.dumps({
#             "parking_id": 1,
#             "sessions": [
#                 {
#                     "client_id": 100000000000000001,
#                     "started_at": 2,
#                     "debt": 1.903,
#                     "updated_at": 1
#                 }
#             ]
#         })
#         response = self._make_signed_json_post(url, body.encode('utf-8'))
#         # print(response)
#         time.sleep(10)
#         self.assertEqual(response.status_code, 202)
#
#     def test_rps_update_valid_body(self):
#         url = '/api/v1/parking/rps/session/list/update/'
#         body = json.dumps({
#             "parking_id":1,
#             "sessions":[
#                 {
#                     "client_id":100000000000000001,
#                     "started_at":1,
#                     "debt":1.903,
#                     "updated_at":1
#                 }
#             ]
#         })
#         response = self._make_signed_json_post(url, body.encode('utf-8'))
#         # print(response)
#         time.sleep(10)
#         self.assertEqual(response.status_code, 202)
