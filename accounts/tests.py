import json
from os import remove
import datetime
from django.test import TestCase
from django.test import Client
from os.path import isfile
from hashlib import md5
import base64
from accounts.models import Account, AccountSession
from parkings.models import Parking, ParkingSession, WantedParking
from vendors.models import Vendor
from parkpass.settings import AVATARS_ROOT
from payments.models import CreditCard, Order, FiskalNotification


class PasswordTestCase(TestCase):
    """
    This test case if for testing /login/restore and /login/changepw
    (Restoring a password by e-mail and changing it manually)
    """

    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test",
            phone="+7(999)4108209",
            email="pashawnn@yandex.ru"
        )

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        account.set_password("qwerty")
        account.save()

        self.client = Client()

    def test_invalid_email_restore(self):
        url = "/account/login/restore"

        body = json.dumps({
            "email": "abra@cadabra.boom"
        })
        response = self.client.post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_email_restore(self):
        url = "/account/login/restore"

        body = json.dumps({
            "email": "pashawnn@yandex.ru"
        })
        response = self.client.post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        print response.content


class LoginEmail1TestCase(TestCase):

    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(910)8271910",
            email="diman-mich@yandex.ru"
        )
        account.set_password("qwerty")
        account.save()

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        self.client = Client()

    def test_invalid_email_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman1-mich@yandex.ru",
            "password": "qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_invalid_email_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman1-mich@yandex.ru",
            "password": "qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_invalid_password_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman-mich@yandex.ru",
            "password": "qwerty1",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman-mich@yandex.ru",
            "password": "qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        print response.content


class LoginEmail2TestCase(TestCase):

    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(910)8271910"
        )
        account.set_password("qwerty")
        account.save()

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

        self.client = Client()

    def test_invalid_email_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman1-mich@yandex.ru",
            "password":"qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_invalid_email_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman1-mich@yandex.ru",
            "password": "qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_login_with_email(self):
        url = "/account/login/email/"

        body = json.dumps({
            "email": "diman-mich@yandex.ru",
            "password": "qwerty",
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content


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
            started_at=datetime.datetime(2017, 12, 13),
            updated_at=datetime.datetime(2017, 12, 14)
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
        page_token = response_dict.get("next", None)

        url = "/account/session/list/?page=%s" % page_token
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content


    def test_parking_session_interval_invalid_params_view(self):

        # skip from_date=11
        url = "/account/session/list/?from_date=11"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 400)
        print response.content

        # skip to_date=11
        url = "/account/session/list/?to_date=11"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 400)
        print response.content

        url = "/account/session/list/?from_date=11&to_date=12"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

        # skip to_date=Privet
        url = "/account/session/list/?to_date=11&to_date=Privet"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content

    def test_parking_session_interval_too_big_period_view(self):
        url = "/account/session/list/?from_date=0&to_date=1527539422"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 400)
        print response.content

    def test_parking_session_interval_valid_view(self):
        url = "/account/session/list/?from_date=1510000000&to_date=1537539422"
        response = self.client.get(url, **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        print "ddd1"
        print response.content
        self.assertEqual(response.status_code, 200)

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
            "id": 15
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        self.assertEqual(response.status_code, 200)
        print response.content


class StartAccountTestCaseWithDebt(TestCase):

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


class ReceiptTestCase(TestCase):

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

        parking_session = ParkingSession.objects.create(
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

        fiskal = FiskalNotification.objects.create(
            fiscal_number=100,
            shift_number=101,
            receipt_datetime = datetime.datetime.now(),
            fn_number="fn_number_sample",
            ecr_reg_number="ecr_reg_number_sample",
            fiscal_document_number=102,
            fiscal_document_attribute=103,
            token="token_sample",
            ofd="ofd",
            url="http://yandex.ru",
            qr_code_url="http://qr_code_url.ru",
            receipt="recept_text",
            type="type_of_notification"
        )

        order = Order.objects.create(
            id=1,
            sum=150,
            payment_attempts=1,
            paid=True,
            session=parking_session,
            account=account,
            fiscal_notification=fiskal
        )


        self.client = Client()

    def test_not_exists_parking(self):
        url = "/account/session/receipt/get/"

        body = json.dumps({
            "id": 3
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

    def test_valid_receipt(self):
        url = "/account/session/receipt/get/"

        body = json.dumps({
            "id": 1
        })

        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 200)
        print response.content


    def test_send_receipt_to_unbinded_mail(self):
        url = "/account/session/receipt/send/"
        body = json.dumps({
            "id": 1
        })
        response = self.client.post(url, body, content_type="application/json",
                                    **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})

        self.assertEqual(response.status_code, 400)
        print response.content

                       
class AccountAvatarTestCase(AccountTestCase):
    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(123)4567890"
        )
        self.client = Client()
        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)

    def test_set_avatar(self):
        url = "/account/avatar/set/"
        with open("test.jpg", "rb") as fp:
            body = json.dumps({
                "avatar": base64.b64encode(fp.read()),
            })
            response = self.client.post(url, body, content_type="application/json",
                                        **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        print response.content
        self.assertEqual(response.status_code, 200)
        phone = "+7(123)4567890"
        path = AVATARS_ROOT + '/' + md5(phone).hexdigest()
        self.assertTrue(isfile(path))
        remove(path)

    def test_get_avatar(self):
        url = "/account/avatar/get/"
        response = self.client.get(url,
                                   **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1'})
        print response.content
        self.assertEqual(response.status_code, 200)


class WantedParkingsTestCase(TestCase):
    def setUp(self):
        account = Account.objects.create(
            id=1,
            first_name="Test1",
            phone="+7(123)4567890"
        )

        account_session = AccountSession(
            token="0ff08840935eb00fad198ef5387423bc24cd15e1",
            account=account
        )
        account_session.set_expire_date()
        account_session.save(not_generate_token=True)
        vendor = Vendor(
            name="test-parking-vendor",
            secret="12345678"
        )
        vendor.save(not_generate_secret=True)
        self.p1 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            enabled=False,
            longitude=1,
            free_places=5,
            vendor=vendor
        )
        self.p2 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            enabled=False,
            longitude=1,
            free_places=5,
            vendor=vendor
        )
        self.p3 = Parking.objects.create(
            name="parking-1",
            description="default",
            enabled=True,
            latitude=1,
            longitude=1,
            free_places=5,
            vendor=vendor
        )
        self.p1.save()
        self.p2.save()
        self.p3.save()
        self.client = Client()

    def test_adding_wannamarks(self):
        print Parking.objects.all()
        resp = []
        for i in [1, 3, 5]:
            url = "/parking/v1/want_parking/%d/" % i
            resp.append(self.client.get(url,
                                        HTTP_AUTHORIZATION='Token 0ff08840935eb00fad198ef5387423bc24cd15e1'))
            print resp[-1].content
        self.assertEqual(resp[0].status_code, 200)
        self.assertEqual(resp[1].status_code, 400)
        self.assertEqual(resp[2].status_code, 400)
        self.assertEqual(WantedParking.get_wanted_count(self.p1), 1)
        self.assertEqual(WantedParking.get_wanted_count(self.p2), 0)
        self.assertEqual(WantedParking.get_wanted_count(self.p3), 0)