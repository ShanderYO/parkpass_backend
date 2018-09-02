import base64
import datetime
import json
from hashlib import md5
from os import remove
from os.path import isfile

from django.test import Client
from django.test import TestCase

from accounts.models import Account, AccountSession
from parkings.models import Parking, ParkingSession, Wish
from parkpass.settings import AVATARS_ROOT
from payments.models import CreditCard, Order, FiskalNotification
from vendors.models import Vendor

TOKEN_DICT = {'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd15e1',
              'content_type': 'application/json'}
TOKEN = "0ff08840935eb00fad198ef5387423bc24cd15e1"
URL_PREFIX = "/api/v1/account/"


def create_account(name="Test", phone="+7(999)1234567", email="test@testing.com", password="qwerty"):
    account = Account(
        first_name=name,
        phone=phone,
        email=email
    )
    account.set_password(password)
    account.save()
    account_session = AccountSession(
        token=TOKEN,
        account=account
    )
    account_session.set_expire_date()
    account_session.save(not_generate_token=True)

    return account, account_session


def create_vendor_parking(ven_name="test-parking-vendor", ven_secret="12345678", park_enabled=True, approved=True,
                          park_name="parking-1", park_desc="default", park_lat=1, park_lon=1, park_places=5):
    v = Vendor(
        display_id=1,
        name=ven_name,
        secret=ven_secret
    )
    v.save(not_generate_secret=True)
    p = Parking.objects.create(
        name=park_name,
        description=park_desc,
        latitude=park_lat,
        enabled=park_enabled,
        longitude=park_lon,
        free_places=park_places,
        max_places=park_places,
        vendor=v,
        approved=approved
    )
    return v, p


class PasswordTestCase(TestCase):
    """
    This test case if for testing /login/restore and /login/changepw
    (Restoring a password by e-mail and changing it manually)
    """

    def setUp(self):
        account, account_session = create_account()
        account.save()

    def test_invalid_email_restore(self):
        """
        Testing case when invalid email is entered when attempting to restore password
        :return:
        """
        url = URL_PREFIX + "password/restore/"

        body = json.dumps({
            "email": "abra@cadabra.boom"
        })
        response = Client().post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_valid_email_restore(self):
        """
        Testing case when valid email is entered when attempting to restore password
        """
        url = URL_PREFIX + "password/restore/"

        body = json.dumps({
            "email": "test@testing.com"
        })
        response = Client().post(url, body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_invalid_old_change(self):
        """
        Testing case when old password is invalid
        """
        url = URL_PREFIX + "password/change/"

        body = json.dumps({
            "old": "abracadabra",
            "new": "12345"
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_valid_password_change(self):
        """
        Testing case when valid old pw entered when changing pw
        """
        url = URL_PREFIX + "password/change/"

        body = json.dumps({
            "old": "qwerty",
            "new": "uiop"
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        # print response.content
        # self.assertTrue(self.account.check_password("uiop"))     # New password should be valid
        # self.assertFalse(self.account.check_password("qwerty"))  # Old password shouldn't


class LoginEmailTestCase(TestCase):

    def setUp(self):
        create_account(email="diman-mich@yandex.ru")

    def test_invalid_email_login_with_email(self):
        url = URL_PREFIX + "login/email/"

        body = json.dumps({
            "email": "diman1-mich@yandex.ru",
            "password": "qwerty",
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_invalid_password_login_with_email(self):
        url = URL_PREFIX + "login/email/"

        body = json.dumps({
            "email": "diman-mich@yandex.ru",
            "password": "qwerty1",
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_valid_login_with_email(self):
        url = URL_PREFIX + "login/email/"
        url2 = URL_PREFIX + "me/"

        body = json.dumps({
            "email": "diman-mich@yandex.ru",
            "password": "qwerty",
        })
        response = Client().post(url, body, **TOKEN_DICT)
        j = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        response = Client().get(url2, content_type='application/json',
                                HTTP_AUTHORIZATION='Token %s' % j['token'])
        self.assertEqual(response.status_code, 200)
        # print response.content


class AccountTestCase(TestCase):
    """
        Test for /api/v1/account/me
    """

    def setUp(self):
        create_account()
        create_vendor_parking()

    def test_invalid_token(self):
        url = URL_PREFIX + "me/"

        response = Client().get(url, content_type="application/json",
                                **{'HTTP_AUTHORIZATION': 'Token 0ff08840935eb00fad198ef5387423bc24cd1523'})
        self.assertEqual(response.status_code, 401)
        j = json.loads(response.content)
        self.assertEqual(102, j['code'])

    def test_valid_request(self):
        url = URL_PREFIX + "me/"

        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        j = json.loads(response.content)
        self.assertEqual(len(j), 7)
        self.assertEqual(1, j['id'])

    def test_new_session_without_card(self):
        url = URL_PREFIX + "session/create/"

        body = json.dumps({
            "session_id": "lala",
            "parking_id": 2,
            "started_at": 1467936000
        })

        response = Client().post(url, body, **TOKEN_DICT)
        self.assertNotEqual(response.status_code, 200)
        j = json.loads(response.content)
        # print json.dumps(j, indent=4), 222333
        # self.assertEqual(305, j['code'])


class AccountDeactivateTestCase(AccountTestCase):
    def setUp(self):
        account, account_session = create_account()
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

        vendor, parking = create_vendor_parking()

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
            state=ParkingSession.STATE_STARTED_BY_CLIENT,
            started_at=datetime.datetime(2016, 12, 13),
            updated_at=datetime.datetime(2016, 12, 13),
            # completed_at=datetime.datetime(2016, 12, 14),
        )
        self.account = account

    def test_deactivate_account(self):
        url = URL_PREFIX + "deactivate/"
        response = Client().post(url, "{}", **TOKEN_DICT)
        # print response.content
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CreditCard.objects.all().count(), 0)
        self.assertIsNone(ParkingSession.get_active_session(account=self.account))


class AccountWithCardTestCase(AccountTestCase):
    def setUp(self):
        account, account_session = create_account()
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

    def test_add_card_request(self):
        url = URL_PREFIX + "card/add/"

        response = Client().post(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)

    def test_set_default_not_exist_card(self):
        url = URL_PREFIX + "card/default/"

        body = json.dumps({
            "id": 3  # not exists
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_change_default_card_repeat(self):
        url = URL_PREFIX + "card/default/"

        body = json.dumps({
            "id": 1  # already by default
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_change_default_card(self):
        url = URL_PREFIX + "card/default/"

        body = json.dumps({
            "id": 2
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_delete_card(self):
        url = URL_PREFIX + "card/delete/"

        body = json.dumps({
            "id": 3  # not exists
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(402, j['code'])

        body = json.dumps({
            "id": 1
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CreditCard.objects.all().count(), 1)


class AccountSessionsTestCase(TestCase):
    def setUp(self):
        vendor, parking = create_vendor_parking()
        account, account_session = create_account()
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
        url = URL_PREFIX + "session/list/"

        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content

        # Check pagination
        response_dict = json.loads(response.content)
        page_token = response_dict.get("next", None)

        url = URL_PREFIX + "session/list/?page=%s" % page_token
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_parking_session_interval_invalid_params_view(self):

        # skip from_date=11
        url = URL_PREFIX + "session/list/?from_date=11"
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        # print response.content

        # skip to_date=11
        url = URL_PREFIX + "session/list/?to_date=11"
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        # print response.content

        url = URL_PREFIX + "session/list/?from_date=11&to_date=12"
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content

        # skip to_date=Privet
        url = URL_PREFIX + "session/list/?to_date=11&to_date=Privet"
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_parking_session_interval_too_big_period_view(self):
        url = URL_PREFIX + "session/list/?from_date=0&to_date=1527539422"
        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        # print response.content

    def test_parking_session_interval_valid_view(self):
        url = URL_PREFIX + "session/list/?from_date=1510000000&to_date=1537539422"
        response = Client().get(url, **TOKEN_DICT)
        # print response.content
        self.assertEqual(response.status_code, 200)

    def test_get_debt_request(self):
        url = URL_PREFIX + "session/debt/"

        response = Client().get(url, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content

    def test_session_pay_invalid_id(self):
        url = URL_PREFIX + "session/pay/"
        body = json.dumps({
            "id": 999  # not exists
        })
        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(402, j['code'])

    def test_session_pay(self):
        url = URL_PREFIX + "session/pay/"

        body = json.dumps({
            "id": 15
        })
        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        # print response.content


class StartAccountTestCaseWithDebt(TestCase):

    def setUp(self):
        vendor, parking = create_vendor_parking()
        account, account_session = create_account()
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
        url = URL_PREFIX + "session/create/"

        body = json.dumps({
            "session_id": "lala",
            "parking_id": 1,
            "started_at": 1467936000
        })

        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(j['code'], 304)

    def test_force_stop_session(self):
        url = URL_PREFIX + "session/stop/"

        body = json.dumps({
            "id": 1
        })

        response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '{}')
        self.assertTrue(ParkingSession.objects.get(id=1).is_suspended)

    def test_force_stop_session_invalid(self):
        url = URL_PREFIX + "session/stop/"

        body = json.dumps({
            "id": 55
        })

        response = Client().post(url, body, **TOKEN_DICT)
        # print response.content, 12321
        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(402, j['code'])

    def test_force_stop_and_resume_session(self):
        url = URL_PREFIX + "session/stop/"

        body = json.dumps({
            "id": 1
        })

        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '{}')
        self.assertTrue(ParkingSession.objects.get(id=1).is_suspended)

        url = URL_PREFIX + "session/resume/"

        body = json.dumps({
            "id": 1
        })

        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '{}')
        self.assertFalse(ParkingSession.objects.get(id=1).is_suspended)


class ReceiptTestCase(TestCase):

    def setUp(self):
        vendor, parking = create_vendor_parking()
        account, account_session = create_account(email=None)
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
            # token="token_sample",
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

    def test_not_exists_parking(self):
        url = URL_PREFIX + "session/receipt/get/"

        body = json.dumps({
            "id": 3
        })

        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(402, j['code'])

    def test_valid_receipt(self):
        url = URL_PREFIX + "session/receipt/get/"

        body = json.dumps({
            "id": 1
        })

        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 200)
        j = json.loads(response.content)
        self.assertEqual(1, j['result'][0]['order']['id'])
        self.assertEqual(1, j['result'][0]['fiscal']['id'])

    def test_send_receipt_to_unbound_mail(self):
        url = URL_PREFIX + "session/receipt/send/"
        body = json.dumps({
            "id": 1
        })
        response = Client().post(url, body, **TOKEN_DICT)

        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(306, j['code'])


class AccountAvatarTestCase(AccountTestCase):
    def setUp(self):
        create_account(phone="+7(123)4567890")

    def test_set_avatar(self):
        url = URL_PREFIX + "avatar/set/"
        with open("test1.jpg", "rb") as fp:
            body = json.dumps({
                "avatar": base64.b64encode(fp.read()),
            })
            response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 200)
        phone = "+7(123)4567890"
        path = AVATARS_ROOT + '/' + md5(phone).hexdigest()
        self.assertTrue(isfile(path))
        remove(path)

    def test_set_large_avatar(self):
        url = URL_PREFIX + "avatar/set/"
        with open("test.jpg", "rb") as fp:
            body = json.dumps({
                "avatar": base64.b64encode(fp.read()),
            })
            response = Client().post(url, body, **TOKEN_DICT)
        self.assertEqual(response.status_code, 400)
        j = json.loads(response.content)
        self.assertEqual(j['code'], 404)
        phone = "+7(123)4567890"
        path = AVATARS_ROOT + '/' + md5(phone).hexdigest()
        self.assertFalse(isfile(path))


class WantedParkingsTestCase(TestCase):
    def setUp(self):
        create_account()
        vendor, self.p1 = create_vendor_parking(park_enabled=False)
        self.p2 = Parking.objects.create(
            name="parking-1",
            description="default",
            latitude=1,
            enabled=False,
            longitude=1,
            max_places=5,
            free_places=5,
            vendor=vendor
        )
        self.p3 = Parking.objects.create(
            name="parking-1",
            description="default",
            enabled=True,
            latitude=1,
            longitude=1,
            max_places=5,
            free_places=5,
            vendor=vendor,
            approved=True
        )
        self.p1.save()
        self.p2.save()
        self.p3.save()

    def test_adding_wannamarks(self):
        # print Parking.objects.all()
        resp = []

        for i in [2, 4, 6]:
            url = "/api/v1/parking/wish/%d/" % i
            resp.append(Client().get(url, **TOKEN_DICT))
            # print resp[-1].content

        w = []
        wishes = Wish.objects.all()
        for wish in wishes:
            w.append(wish)

        self.assertEqual(resp[0].status_code, 200)
        self.assertEqual(resp[1].status_code, 400)
        self.assertEqual(resp[2].status_code, 400)
        self.assertEqual(Wish.get_wanted_count(self.p1), 1)
        self.assertEqual(Wish.get_wanted_count(self.p2), 0)
        self.assertEqual(Wish.get_wanted_count(self.p3), 0)
