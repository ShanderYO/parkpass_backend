import json

import datetime
from django.test import TestCase
from django.test import Client

# Create your tests here.
from accounts.models import Account, AccountSession
from parkings.models import Vendor, Parking, ParkingSession
from payments.models import CreditCard, Order


class AccountBaseTestCase(TestCase):
    """
        Test for /account/me API method request without user
    """

    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(910)8271910",
        )
        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        self.client = Client()

    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)

        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)


    """
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
    """

"""
class LoginTestCase(TestCase):

    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 415)
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)


class LogoutTestCase(TestCase):

    def test_content_type_url(self):
        url = "/account/login/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 415)
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)

"""

class AccountTestCase(TestCase):
    """
        Test for /account/me
    """

    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(910)8271910",
        )
        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        self.client = Client()

    def test_invalid_token(self):
        url = "/account/me/"

        response = self.client.get(url, content_type="application/json", **{'HTTP_AUTHORIZATION':'Token 0ff08840935eb00fad198ef5387423bc24cd15e0'})
        self.assertEqual(response.status_code, 401)
        print response.content

    def test_valid_request(self):
        url = "/account/me/"

        response = self.client.get(url, **{'HTTP_AUTHORIZATION': "Token 0ff08840935eb00fad198ef5387423bc24cd15e1"})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_new_session_without_card(self):
        # TODO check for creating
        pass


class AccountWithCardTestCase(AccountTestCase):
    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(910)8271910",
        )
        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        CreditCard.objects.create(
            id=1,
            pan="3242****3241",
            exp_date="1118",
            is_default=True,
            account=account,
        )

        CreditCard.objects.create(
            id=2,
            pan="3242****3242",
            exp_date="0916",
            is_default=False,
            account=account,
        )
    """
    def test_add_card_request(self):
        url = "/account/card/add/"

        response = self.client.post(url, content_type="application/json",
                                   **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content
    """

    def test_set_default_not_exist_card(self):
        url = "/account/card/default/"

        body = json.dumps({
            "id": 3  # not exists
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_change_default_card_repeat(self):
        url = "/account/card/default/"

        body = json.dumps({
            "id": 1 # already by default
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        print response.content

    def test_change_default_card(self):
        url = "/account/card/default/"

        body = json.dumps({
            "id": 2
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        print response.content

    def test_delete_card(self):
        url = "/account/card/delete/"

        body = json.dumps({
            "id": 3 # not exists
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

        body = json.dumps({
            "id": 1
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        self.assertEquals(CreditCard.objects.all().count(), 1)
        print response.content


class AccountSessionsTestCase(TestCase):
    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking = Parking.objects.create(
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

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        ParkingSession.objects.create(
            id=1,
            session_id="session_1",
            client=account,
            parking=parking,
            debt=100,
            state=ParkingSession.STATE_CLOSED,
            started_at=datetime.datetime(2016, 12, 14),
            updated_at=datetime.datetime(2016, 12, 14),
            completed_at=datetime.datetime(2016, 12, 15),
        )

        ParkingSession.objects.create(
            id=2,
            session_id="session_2",
            client=account,
            parking=parking,
            debt=120,
            state=ParkingSession.STATE_CLOSED,
            started_at=datetime.datetime(2016, 12, 13),
            updated_at=datetime.datetime(2016, 12, 13),
            completed_at=datetime.datetime(2016, 12, 14),
        )

        # For pagination test
        for i in range(3, 10):
            ParkingSession.objects.create(
                session_id="session_"+str(i),
                client=account,
                parking=parking,
                debt=120,
                state=ParkingSession.STATE_CLOSED,
                started_at=datetime.datetime(2016, i, i),
                updated_at=datetime.datetime(2016, i, i+1),
                completed_at=datetime.datetime(2016, i, i+1),
            )

        # Create active account session
        active_session = ParkingSession.objects.create(
            id=15,
            session_id="session_15",
            client=account,
            parking=parking,
            debt=120,
            state=ParkingSession.STATE_COMPLETED,
            started_at=datetime.datetime(2016, 12, 13),
            updated_at=datetime.datetime(2016, 12, 14)
        )

        # Create order for account session
        Order.objects.create(
            id=1,
            sum=20,
            payment_attempts=1,
            paid=True,
            session=active_session,
            account=account,
        )
        Order.objects.create(
            id=2,
            sum=20,
            payment_attempts=1,
            paid=False,
            session=active_session,
            account=account,
        )

    def test_parking_session_list_page(self):
        url = "/account/session/list/"

        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

        # Check pagination
        response_dict = json.loads(response.content)
        page_token = response_dict["next"]

        url = "/account/session/list/?page=%s" % page_token
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_get_debt_request(self):
        url = "/account/session/debt/"

        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_session_pay_invalid_id(self):
        url = "/account/session/pay/"
        body = json.dumps({
            "id": 999  # not exists
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 400)
        print response.content

    def test_session_pay(self):
        url = "/account/session/pay/"

        body = json.dumps({
            "id": 15  # not exists
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content


class StartAccountTestCaseWithDebt(TestCase):
    """
        Test for /account/session/start
    """

    def setUp(self):
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)

        parking = Parking.objects.create(
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

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        # Create active account session
        ParkingSession.objects.create(
            id=1,
            session_id="session_10",
            client=account,
            parking=parking,
            debt=120,
            state=ParkingSession.STATE_CLOSED,
            started_at=datetime.datetime(2016, 12, 12),
            updated_at=datetime.datetime(2016, 12, 13)
        )

        # Create active account session
        active_session = ParkingSession.objects.create(
            id=2,
            session_id="session_15",
            client=account,
            parking=parking,
            debt=120,
            state=ParkingSession.STATE_COMPLETED,
            started_at=datetime.datetime(2016, 12, 13),
            updated_at=datetime.datetime(2016, 12, 14)
        )

    def test_denied_start_session(self):
        url = "/account/session/create/"

        body = json.dumps({
            "session_id":"lala",
            "parking_id":1,
            "started_at":1467936000
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 400)
        print response.content

    def test_force_stop_session(self):
        url = "/account/session/stop/"

        body = json.dumps({
            "id": 1
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_force_stop_session_invalid(self):
        url = "/account/session/stop/"

        body = json.dumps({
            "id": 1
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_force_stop_and_resume_session(self):
        url = "/account/session/stop/"

        body = json.dumps({
            "id": 1
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        print response.content

    def test_force_stop_and_start_new(self):
        pass


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

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        self.client = Client()


