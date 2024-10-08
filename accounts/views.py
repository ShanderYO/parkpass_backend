# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from decimal import Decimal

import qrcode
import qrcode.image.svg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django_elasticsearch.client import es_client

from dss.Serializer import serializer

from accounts.models import Account, AccountSession

from accounts.tasks import generate_current_debt_order, force_pay
from accounts.validators import LoginParamValidator, ConfirmLoginParamValidator, AccountParamValidator, IdValidator, \
    StartAccountParkingSessionValidator, CompleteAccountParkingSessionValidator, EmailValidator, \
    EmailAndPasswordValidator, ExternalLoginValidator, UsersLogValidator
from base.exceptions import AuthException, ValidationException, PermissionException, PaymentException
from base.models import EmailConfirmation
from base.utils import clear_phone, elastic_log
from base.utils import get_logger, parse_int, datetime_from_unix_timestamp_tz
from base.views import APIView, LoginRequiredAPIView, ObjectView, SignedRequestAPIView
from notifications.models import AccountDevice
from owners.models import OwnerIssue, Owner
from parkings.models import ParkingSession, Parking
from parkpass_backend.settings import DEFAULT_AVATAR_URL, ZENDESK_MOBILE_SECRET, ZENDESK_CHAT_SECRET, \
    ES_APP_BLUETOOTH_LOGS_INDEX_NAME, ES_APP_ENTER_APP_LOGS_INDEX_NAME, \
    ES_APP_SESSION_PAY_LOGS_INDEX_NAME
from payments.models import CreditCard, Order
from payments.utils import TinkoffExceptionAdapter
from rps_vendor.models import RpsSubscription, RpsParkingCardSession

from accounts.sms_gateway import sms_sender

from vendors.models import VendorIssue, Vendor


class SetAvatarView(LoginRequiredAPIView):
    def post(self, request):
        try:
            file = request.data.get("avatar", None)
            if file is None:
                raise ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "No file attached"
                )
            request.account.update_avatar(base64.b64decode(file))
        except ValidationException as e:
            return JsonResponse(e.to_dict(), status=400)
        return JsonResponse({}, status=200)


class PasswordChangeView(LoginRequiredAPIView):
    """
    API View for url /login/changepw
    In: POST with json { old: "old_password", new: "new_password" }
    Out:
    200 {}

    """

    def post(self, request):
        old_password = request.data["old"]
        new_password = request.data["new"]

        account = request.account

        if not account.check_password(old_password):
            e = AuthException(
                AuthException.INVALID_PASSWORD,
                "Invalid old password"
            )
            return JsonResponse(e.to_dict(), status=400)
        account.set_password(new_password)
        return JsonResponse({}, status=200)


class DeactivateAccountView(LoginRequiredAPIView):
    """
    API View for url /account/deactivate
    Clear card list and stop parking session
    Out: {} 200
    """

    def post(self, request):
        account = request.account
        ps = ParkingSession.get_active_session(account)
        if ps is not None:
            generate_current_debt_order.delay(ParkingSession.get_active_session(account).id)
            if not ps.is_suspended:
                ps.is_suspended = True
                ps.suspended_at = timezone.now()
                ps.save()

        cards = CreditCard.objects.filter(account=account)
        for card in cards:
            card.delete()

        return JsonResponse({}, status=200)


class OwnerIssueView(APIView):
    def get(self, request, *args, **kwargs):
        response = {
            "result":serializer(OwnerIssue.objects.all())
        }
        return JsonResponse(response, status=200)

    def post(self, request, *args, **kwargs):
        name = request.data.get("name", "")
        phone = request.data.get("phone", "")
        email = request.data.get("email", "")

        if phone == "" and email == "":
            return JsonResponse({"error": "Error %s %s" % (phone, email)}, status=400)

        issue = OwnerIssue(
            name=name,
            phone=phone,
            email=email
        )
        issue.save()
        text = u"Ваша заявка принята в обработку. С Вами свяжутся в ближайшее время."
        if issue.phone:
            get_logger().info("Send to  phone %s" % issue.phone)
            sms_sender.send_message(issue.phone, text)

        if issue.email:
            get_logger().info("Send to  email %s " % issue.email)
            issue.send_mail(issue.email)

        return JsonResponse({}, status=200)


class VendorIssueView(APIView, ObjectView):
    object = VendorIssue
    methods = ('POST',)
    show_fields = ('name', 'phone', 'email')

    def on_create(self, request, obj):
        name = request.data.get("name", "")
        phone = request.data.get("phone", "")
        email = request.data.get("email", "")
        issue = VendorIssue(
            name=name,
            phone=phone,
            email=email
        )
        issue.save()
        text = u"Ваша заявка принята в обработку. С Вами свяжутся в ближайшее время."
        if phone:
            sms_sender.send_message(issue.phone, text)
        if email:
            issue.send_mail(email)


class LoginView(APIView):
    validator_class = LoginParamValidator

    def post(self, request):
        
        # ban = ['176.59', '213.87', '178.176', '188.162', '31.173']
        
        # def get_client_ip(request):
        #     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        #     if x_forwarded_for:
        #         ip = x_forwarded_for.split(',')[0]
        #     else:
        #         ip = request.META.get('REMOTE_ADDR')
        #     return ip
        
        # ip = get_client_ip(request)
        # if any(ip.startswith(i) for i in ban):
        #     return JsonResponse({}, status=403)
        
        phone = clear_phone(request.data["phone"])
        success_status = 200
        if Account.objects.filter(phone=phone).exists():
            account = Account.objects.get(phone=phone)
        else:
            account = Account(phone=phone)
            success_status = 201

        account.create_sms_code(stub=(phone == "77891234560"))
        account.sms_verified = False
        account.save()

        # Send sms
        if phone == "77891234560":
            return JsonResponse({}, status=200)

        sms_sender.send_message(account.phone,
                             u"Код подтверждения %s" % (account.sms_code,))
        # if sms_sender.exception:
        #     return JsonResponse(sms_sender.exception.to_dict(), status=400)

        return JsonResponse({}, status=success_status)


class ConfirmLoginView(APIView):
    validator_class = ConfirmLoginParamValidator

    def post(self, request):
        sms_code = request.data["sms_code"]
        try:
            account = Account.objects.get(sms_code=sms_code)
            account.sms_verified = True
            account.save()
            account.login()
            session = account.get_session()
            return JsonResponse(serializer(session, exclude_attr=("created_at",)))

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Account with pending sms-code not found")
            return JsonResponse(e.to_dict(), status=400)


class PasswordRestoreView(APIView):
    """
    API View for url /login/restore
    In: POST with json { email: "my@mail.ru" (String) }
    Out:
      200 {}, sending an email with new pw
      400 { AuthException User with such email not found }
    """
    validator_class = EmailValidator

    def post(self, request):
        email = request.data["email"].lower()

        try:
            account = Account.objects.get(email=email)
            account.create_password_and_send(is_recovery=True)
            return JsonResponse({}, status=200)
        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found"
            )
            return JsonResponse(e.to_dict(), status=400)


class LoginWithEmailView(APIView):
    validator_class = EmailAndPasswordValidator

    def post(self, request):
        raw_email = request.data["email"]
        password = request.data["password"]
        email = raw_email.lower()

        try:
            account = Account.objects.get(email=email)
            if account.check_password(raw_password=password):
                if AccountSession.objects.filter(account=account).exists():
                    session = AccountSession.objects.filter(account=account).order_by('-created_at')[0]
                    response_dict = serializer(session)
                    return JsonResponse(response_dict)
                else:
                    e = AuthException(
                        AuthException.INVALID_SESSION,
                        "Invalid session. Login with phone required"
                    )
                    return JsonResponse(e.to_dict(), status=400)
            else:
                e = AuthException(
                    AuthException.INVALID_PASSWORD,
                    "Invalid password"
                )
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "User with such email not found")
            return JsonResponse(e.to_dict(), status=400)


class LogoutView(LoginRequiredAPIView):
    def post(self, request):
        request.account.clean_session()
        return JsonResponse({}, status=200)


class AccountView(LoginRequiredAPIView):
    validator_class = AccountParamValidator

    def get(self, request):
        account_dict = serializer(request.account, exclude_attr=("created_at", "sms_code", "password"))
        card_list = CreditCard.get_card_by_account(request.account)
        account_dict["cards"] = serializer(card_list, include_attr=("id", "pan", "exp_date", "is_default"))

        if account_dict["avatar"]:
            account_dict["avatar"] = request.get_host() + account_dict["avatar"]
        else:
            account_dict["avatar"] = request.get_host() + DEFAULT_AVATAR_URL

        elastic_log(ES_APP_ENTER_APP_LOGS_INDEX_NAME, "Online", account_dict)

        return JsonResponse(account_dict, status=200)

    def post(self, request):
        first_name = request.data.get("first_name")
        if first_name:
            request.account.first_name = first_name
        last_name = request.data.get("last_name")
        if last_name:
            request.account.last_name = last_name
        email_fiskal_notification_enabled = request.data.get("email_fiskal_notification_enabled")
        if email_fiskal_notification_enabled:
            if str(email_fiskal_notification_enabled) == '1':
                request.account.email_fiskal_notification_enabled = True
            elif str(email_fiskal_notification_enabled) == '0':
                request.account.email_fiskal_notification_enabled = False
        request.account.save()

        return JsonResponse({}, status=200)

class GetAccountIdQr(LoginRequiredAPIView):
    validator_class = AccountParamValidator

    def get(self, request):
        account_dict = serializer(request.account, exclude_attr=("id",))
        account_id = account_dict['id']
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(account_id, image_factory=factory, box_size=20)
        response = HttpResponse()
        img.save(response)
        return response

class AccountParkingListView(LoginRequiredAPIView):
    max_paginate_length = 10
    max_select_time_interval = 366 * 24 * 60 * 60 # 1 year

    def get(self, request, *args, **kwargs):
        page = parse_int(request.GET.get("page", None))
        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) > self.max_select_time_interval:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Max time interval exceeded. Max value %s, accepted %s" % (self.max_select_time_interval,
                                                                               (to_date-from_date))
                )
                return JsonResponse(e.to_dict(), status=400)

        result_query = ParkingSession.objects.filter(
            Q(client_id=request.account.id, state__lte=0) | Q(client_id=request.account.id, is_suspended=True))\
            .select_related("parking")

        if from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)

            result_query = result_query.filter(
                created_at__gt=from_date_datetime, created_at__lt=to_date_datetime).order_by("-id")

        if page:
            id = int(page)
            result_query = result_query.filter(pk__lt=id).order_by("-id")

        object_list = result_query[:self.max_paginate_length]
        data = serializer(object_list, foreign=False, exclude_attr=("session_id", "extra_data", "client_id",
                                                                    "parking_id", "created_at"))
        for index, obj in enumerate(object_list):
            parking_dict = {
                "id": obj.parking.id,
                "name": obj.parking.name
            }
            data[index]["parking"] = parking_dict

        response = {
            "result": data
        }
        if len(data) == self.max_paginate_length:
            response["next"] = str(data[self.max_paginate_length - 1]["id"])
        return JsonResponse(response)

class AccountParkingAllHistoryView(LoginRequiredAPIView):
# class AccountParkingAllHistoryView(APIView):
    max_paginate_length = 10
    max_select_time_interval = 366 * 24 * 60 * 60 # 1 year

    def get(self, request, *args, **kwargs):
        from_date = parse_int(request.GET.get("from_date", None))
        to_date = parse_int(request.GET.get("to_date", None))
        client_id = request.account.id
        # client_id = 100000000000000003

        if from_date or to_date:
            if from_date is None or to_date is None:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "from_date and to_date unix-timestamps are required"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) <= 0:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Key 'to_date' must be more than 'from_date' key"
                )
                return JsonResponse(e.to_dict(), status=400)

            if (to_date - from_date) > self.max_select_time_interval:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Max time interval exceeded. Max value %s, accepted %s" % (self.max_select_time_interval,
                                                                               (to_date-from_date))
                )
                return JsonResponse(e.to_dict(), status=400)

        parking_result_query = ParkingSession.objects.filter(
            Q(client_id=client_id, state__lte=0) | Q(client_id=client_id, is_suspended=True))\
            .select_related("parking")

        subscription_qs = RpsSubscription.objects.filter(
            account_id=client_id
        ).select_related('parking')


        parkingcard_session_result_query = RpsParkingCardSession.objects.filter(
            account_id=client_id
        )


        if from_date and to_date:
            from_date_datetime = datetime_from_unix_timestamp_tz(from_date)
            to_date_datetime = datetime_from_unix_timestamp_tz(to_date)

            parking_result_query = parking_result_query.filter(
                created_at__gt=from_date_datetime, created_at__lt=to_date_datetime).order_by("-id")
            subscription_qs.filter(
                started_at__gt=from_date_datetime, started_at__lt=to_date_datetime).order_by("-id")
            parkingcard_session_result_query.filter(
                created_at__gt=from_date_datetime, created_at__lt=to_date_datetime).order_by("-id")

        # object_list = result_query[:self.max_paginate_length]
        # object_list = parking_result_query

        parking_data = serializer(parking_result_query, foreign=False, exclude_attr=("session_id", "extra_data", "client_id",
                                                                    "parking_id", "created_at"))

        for index, obj in enumerate(parking_result_query):
            parking_dict = {
                "id": obj.parking.id,
                "name": obj.parking.name,
                "address": obj.parking.address
            }
            parking_data[index]["parking"] = parking_dict
            parking_data[index]["item_type"] = 'session'
            parking_data[index]["date_for_order"] = obj.created_at

            order = Order.objects.filter(session_id=obj.id, paid=True).select_related(
                'fiscal_notification').first()
            if order:
                parking_data[index]["payment_time"] = order.created_at
                parking_data[index]["fiskal"] = serializer(
                    order.fiscal_notification, include_attr=('id', 'url'))
            else:
                parking_data[index]["payment_time"] = None
                parking_data[index]["fiskal"] = None



        serialized_subs = serializer(subscription_qs,
                                     include_attr=('id', 'name', 'description', 'sum', 'data', 'started_at',
                                                   'expired_at', 'duration', 'prolongation', 'unlimited',
                                                   'state', 'active', 'error_message',))
        for index, sub in enumerate(subscription_qs):
            serialized_subs[index]["parking"] = serializer(
                sub.parking, include_attr=('id', 'name', 'description', 'address'))
            serialized_subs[index]["item_type"] = 'subscription'
            serialized_subs[index]["date_for_order"] = sub.started_at
            order = Order.objects.filter(subscription_id=sub.id, paid=True).select_related('fiscal_notification').first()
            if order:
                serialized_subs[index]["payment_time"] = order.created_at
                serialized_subs[index]["fiskal"] = serializer(
                    order.fiscal_notification, include_attr=('id', 'url'))
            else:
                serialized_subs[index]["payment_time"] = None
                serialized_subs[index]["fiskal"] = None

        parkingcard_session_data = serializer(parkingcard_session_result_query)

        for index, obj in enumerate(parkingcard_session_result_query):
            parkingcard_session_data[index]["item_type"] = 'parking_card_session'
            parkingcard_session_data[index]["date_for_order"] = obj.created_at

            parkingcard_session_data[index]["parking"] = serializer(
                Parking.objects.get(id=obj.parking_id), include_attr=('id', 'name', 'description', 'address'))

            order = Order.objects.filter(parking_card_session_id=obj.id, paid=True).select_related(
                'fiscal_notification').first()
            if order:
                parkingcard_session_data[index]["payment_time"] = order.created_at
                parkingcard_session_data[index]["fiskal"] = serializer(
                    order.fiscal_notification, include_attr=('id', 'url'))
            else:
                parkingcard_session_data[index]["payment_time"] = None
                parkingcard_session_data[index]["fiskal"] = None

        array = parking_data + serialized_subs + parkingcard_session_data

        array = sorted(
            array,
            key=lambda x: x['date_for_order'].strftime('%s'), reverse=True
        )

        response = {
            "result": array
        }

        return JsonResponse(response)

class DebtParkingSessionView(LoginRequiredAPIView):
    def get(self, request):
        current_parking_session = ParkingSession.get_active_session(request.account)
        if current_parking_session:
            debt_dict = serializer(current_parking_session, exclude_attr=("session_id", "client_id", "extra_data", "created_at",))
            orders = Order.objects.filter(session=current_parking_session)
            orders_dict = serializer(orders, foreign=False, include_attr=("id", "sum", "authorized", "paid"))
            debt_dict["orders"] = orders_dict

            elastic_log(ES_APP_SESSION_PAY_LOGS_INDEX_NAME, "Get debt", {
                'debt_dict': serializer(debt_dict),
                'account': serializer(request.account, exclude_attr=("created_at", "sms_code", "password"))
            })

            return JsonResponse(debt_dict, status=200)
        else:
            return JsonResponse({}, status=200)


class GetReceiptView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = int(request.data["id"])
        try:
            parking_session = ParkingSession.objects.get(id=id)
            orders = Order.objects.filter(session=parking_session, paid=True)

            response = {"result": []}
            for order in orders:
                response["result"].append(order.get_order_with_fiscal_dict())
            return JsonResponse(response, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)

class GetReceiptCheckUrlView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = int(request.data["id"])
        try:
            parking_session = ParkingSession.objects.get(id=id)
            orders = Order.objects.filter(session=parking_session, paid=True)

            response = {"result": []}
            for order in orders:
                response["result"].append(order.get_order_with_fiscal_check_url_dict())
            return JsonResponse(response, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)

class SendReceiptToEmailView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = int(request.data["id"])
        if request.account.email is None:
            e = PermissionException(
                PermissionException.EMAIL_REQUIRED,
                "Your account doesn't have binded email"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            parking_session = ParkingSession.objects.get(id=id)
            for order in Order.objects.filter(session=parking_session):
                order.send_receipt_to_email()
            return JsonResponse({}, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)


class ChangeEmailView(LoginRequiredAPIView):
    validator_class = EmailValidator

    def post(self, request):
        email = str(request.data["email"])
        current_account = request.account
        email_confirmation = None

        # check already added email
        if current_account.email == email:
            e = ValidationException(
                ValidationException.ALREADY_EXISTS,
                "Such email is already binded to this account"
            )
            return JsonResponse(e.to_dict(), status=400)

        # check non-unique email
        if Account.objects.filter(email=email).exists():
            e = ValidationException(
                ValidationException.EMAIL_ALREADY_USED,
                "Such email is already binded to another account"
            )
            return JsonResponse(e.to_dict(), status=400)

        # get if already exists
        email_confirmation_list = EmailConfirmation.objects.filter(email=email)
        if email_confirmation_list.exists():
            email_confirmation = email_confirmation_list[0]

        # create new confirmation
        if email_confirmation is None:
            email_confirmation = EmailConfirmation(email=email)

        email_confirmation.create_code()
        email_confirmation.save()

        current_account.email_confirmation = email_confirmation
        current_account.save()

        email_confirmation.send_confirm_mail()
        return JsonResponse({}, status=200)



class EmailConfirmationView(View):
    def get(self, request, *args, **kwargs):
        confirmations = EmailConfirmation.objects.filter(code=kwargs["code"])
        if confirmations.exists():
            confirmation = confirmations[0]
            if confirmation.is_expired():
                return JsonResponse({"error": "Link is expired"}, status=200)
            else:
                try:
                    account = Account.objects.get(email_confirmation=confirmation)
                    if account.email:
                        account.email = confirmation.email
                        account.email_confirmation = None
                        account.create_password_and_send()
                        account.save()
                        confirmation.delete()
                        return render(request, 'client_pages/email_activated.html')
                        # return JsonResponse({"message": "Email is activated successfully"})
                    else:
                        account.email = confirmation.email
                        account.email_confirmation = None
                        account.save()
                        confirmation.delete()
                        return render(request, 'client_pages/email_activated.html')
                        # return JsonResponse({"message": "Email is activated successfully"})

                except ObjectDoesNotExist:
                    return JsonResponse({"error": "Email was changes successfully"}, status=200)

        else:
            return JsonResponse({"error": "Invalid link"}, status=200)


class ForcePayView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        parking_session_id = int(request.data["id"])
        try:
            parking_session = ParkingSession.objects.get(id=parking_session_id)
            # Create payment order and pay
            if parking_session_id:
                get_logger().info("try force_pay.delay id - %s" % parking_session_id)
                force_pay(parking_session_id)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session with id %s does not exist" % id)
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class AddCardView(LoginRequiredAPIView):
    def post(self, request):
        last_active_session = ParkingSession.get_active_session(request.account)
        acquiring = 'tinkoff'

        geo = request.POST.get("geo", False)
        if request.account.country:
            if request.account.country.slug == 'kz':
                acquiring = 'homebank'
        else:
            if request.account.phone[1:6] == "WWW98181" or request.account.phone[1:4] in ["700", "701", "702", "703", "704", "705", "706", "707", "708", "709", "747", "750", "751", "760", "761", "762", "763", "764", "771", "775", "776", "777", "778"]:
                acquiring = 'homebank'

        result_dict = CreditCard.bind_request(request.account, acquiring=acquiring)
        # If error request
        if not result_dict:
            e = PaymentException(
                PaymentException.BAD_PAYMENT_GATEWAY,
                "Payment gateway temporary not available"
            )
            return JsonResponse(e.to_dict(), status=400)

        # If exception occurs
        if result_dict.get("exception", None):
            exception = result_dict["exception"]
            error_code = int(exception.get("error_code", 0))
            error_message = exception.get("error_message", "")
            error_details = exception.get("error_details", "")

            get_logger().warning("Init exception: " + str(error_code) +
                                 " : " + error_message + " : " + error_details)

            exception_adapter = TinkoffExceptionAdapter(error_code)
            e = exception_adapter.get_api_exeption()
            return JsonResponse(e.to_dict(), status=400)

        # Success result
        return JsonResponse({
            "payment_url": result_dict["payment_url"]
        }, status=200)

class AddCardTestView(APIView):
    def get(self, request):

        # return JsonResponse({
        #     "payment_url": 'good 111'
        # }, status=200)

        account = Account.objects.get(id=15)

        # acquiring = 'homebank'

        result_dict = CreditCard.bind_request(account, acquiring='tinkoff')
        # If error request
        if not result_dict:
            e = PaymentException(
                PaymentException.BAD_PAYMENT_GATEWAY,
                "Payment gateway temporary not available"
            )
            return JsonResponse(e.to_dict(), status=400)

        # If exception occurs
        if result_dict.get("exception", None):
            exception = result_dict["exception"]
            error_code = int(exception.get("error_code", 0))
            error_message = exception.get("error_message", "")
            error_details = exception.get("error_details", "")

            get_logger().warning("Init exception: " + str(error_code) +
                                 " : " + error_message + " : " + error_details)

            exception_adapter = TinkoffExceptionAdapter(error_code)
            e = exception_adapter.get_api_exeption()
            return JsonResponse(e.to_dict(), status=400)

        # Success result
        return JsonResponse({
            "payment_url": result_dict["payment_url"]
        }, status=200)


class DeleteCardView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        card_id = request.data["id"]
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your card with such id not found")
            return JsonResponse(e.to_dict(), status=400)

        if CreditCard.objects.filter(account=request.account).count() > 1:
            if not card.is_default:
                card.delete()
            else:
                card.delete()
                another_card = CreditCard.objects.filter(account=request.account)[0]
                another_card.is_default = True
                another_card.save()
        else:
            e = PermissionException(
                PermissionException.ONLY_ONE_CARD,
                "Impossible to delete single card"
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class SetDefaultCardView(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        card_id = request.data["id"]
        try:
            card = CreditCard.objects.get(id=card_id, account=request.account)
        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your card with such id not found")
            return JsonResponse(e.to_dict(), status=400)

        default_card = CreditCard.objects.get(account=request.account, is_default=True)
        default_card.is_default=False
        default_card.save()

        card.is_default = True
        card.save()
        return JsonResponse({}, status=200)


class GetParkingSessionView(LoginRequiredAPIView):
    def get(self, request, **kwargs):
        parking_id = int(kwargs["pk"])
        try:
            parking_session = ParkingSession.objects.get(id=parking_id, client=request.account)
            result_dict = serializer(parking_session, foreign=False, exclude_attr=("client_id",))
            return JsonResponse(result_dict, status=200)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking with id %s does not exist" % parking_id)
            return JsonResponse(e.to_dict(), status=400)


class StartParkingSession(LoginRequiredAPIView):
    validator_class = StartAccountParkingSessionValidator

    def post(self, request):
        session_id = request.data["session_id"]
        parking_id = int(request.data["parking_id"])
        started_at = int(request.data["started_at"])
        extra_data = request.data.get("extra_data", None)

        # Check open session
        if ParkingSession.get_active_session(request.account):
            e = PermissionException(
                PermissionException.ONLY_ONE_ACTIVE_SESSION_REQUIRED,
                "It's impossible to create second active session")
            return JsonResponse(e.to_dict(), status=400)

        if not CreditCard.objects.filter(account=request.account).exists():
            e = PermissionException(
                PermissionException.CREDIT_CARD_REQUIRED,
                "It's impossible to create session without credit card"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            parking_session = ParkingSession.objects.get(
                session_id=session_id, parking_id=parking_id
            )
            parking_session.extra_data = extra_data
            parking_session.add_client_start_mark()
            parking_session.save()
            return JsonResponse({"id": parking_session.id}, status=200)

        except ObjectDoesNotExist:
            try:
                parking = Parking.objects.get(id=parking_id)
            except ObjectDoesNotExist:
                e = ValidationException(
                    ValidationException.RESOURCE_NOT_FOUND,
                    "Parking with id %s does not exist" % parking_id)
                return JsonResponse(e.to_dict(), status=400)

            utc_started_at = parking.get_utc_parking_datetime(started_at)

            parking_session = ParkingSession.objects.create(
                session_id=session_id,
                client=request.account,
                parking=parking,
                extra_data=extra_data,
                state=ParkingSession.STATE_STARTED_BY_CLIENT,
                started_at=utc_started_at
            )
            parking_session.save()

            # Событие въезда
            device_for_push_notification = AccountDevice.objects.filter(account=request.account, active=True)[0]
            # if device_for_push_notification:
            #     device_for_push_notification.send_message(title='Оповещение ParkPass', body='Въезд')

            elastic_log(ES_APP_SESSION_PAY_LOGS_INDEX_NAME, "Start session", {
                'parking_session': serializer(parking_session),
                'parking_id': parking_id,
                'started_at': started_at,
                'account': serializer(request.account, exclude_attr=("created_at", "sms_code", "password"))
            })

            return JsonResponse({"id": parking_session.id}, status=200)


class ForceStopParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = int(request.data["id"])

        try:
            parking_session = ParkingSession.objects.get(id=id)
            if not parking_session.is_suspended:
                parking_session.is_suspended = True
                parking_session.suspended_at = timezone.now()
                parking_session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with id %s not found" % id
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ResumeParkingSession(LoginRequiredAPIView):
    validator_class = IdValidator

    def post(self, request):
        id = int(request.data["id"])

        try:
            parking_session = ParkingSession.objects.get(id=id)
            if parking_session.is_suspended:
                parking_session.is_suspended = False
                parking_session.suspended_at = None
                parking_session.save()

                if parking_session.is_started_by_vendor():
                    generate_current_debt_order.delay(parking_session.id)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "ParkingSession with id %s not found" % id
            )
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class CompleteParkingSession(LoginRequiredAPIView):
    validator_class = CompleteAccountParkingSessionValidator

    def post(self, request):
        session_id = request.data["id"]
        parking_id = int(request.data["parking_id"])
        completed_at = int(request.data["completed_at"])
        sum_to_pay = abs(Decimal(request.data.get('sum', 0)))

        try:
            parking_session = ParkingSession.objects.select_related('parking').get(
                session_id=session_id,
                parking_id=parking_id,
                client=request.account
            )

            # It's needed only for account session completed
            utc_completed_at = parking_session.parking.get_utc_parking_datetime(completed_at)

            # if session is already not active
            if parking_session.state == ParkingSession.STATE_VERIFICATION_REQUIRED:
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Parking session verification required")
                return JsonResponse(e.to_dict(), status=400)

            # If session start is not confirm from vendor
            if not parking_session.is_started_by_vendor():
                parking_session.is_suspended = True
                parking_session.suspended_at = utc_completed_at
                parking_session.save()
                return JsonResponse({}, status=200)
            else:
                parking_session.is_suspended = False

            # Set up completed time if not specified by vendor
            if not parking_session.is_completed_by_vendor():
                parking_session.completed_at = utc_completed_at

            parking_session.add_client_complete_mark()

            # holding
            if sum_to_pay:
                session_orders = parking_session.get_session_orders()

                for order in session_orders:
                    order.try_pay()
                    sum_to_pay = sum_to_pay - order.sum

                if sum_to_pay:
                    new_order = Order.objects.create(
                        session=parking_session,
                        sum=sum_to_pay,
                        acquiring=parking_session.parking.acquiring)
                    new_order.try_pay()
            # end holding

            elastic_log(ES_APP_SESSION_PAY_LOGS_INDEX_NAME, "Complete session", {
                'parking_session': serializer(parking_session),
                'account': serializer(request.account, exclude_attr=("created_at", "sms_code", "password")),
                'sum_to_pay': sum_to_pay,
                'completed_at': completed_at,
                'parking_id': parking_id
            })

            parking_session.save()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Parking session does not exist")
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ZendeskUserJWTChatView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        name = None
        if request.owner:
            jwt_token = request.owner.get_or_create_jwt_for_zendesk(ZENDESK_CHAT_SECRET)
            return HttpResponse(jwt_token)
        else:
            jwt_token = request.account.get_or_create_jwt_for_zendesk(ZENDESK_CHAT_SECRET)
            return HttpResponse(jwt_token)


class ZendeskUserJWTMobileView(View):
    def get(self, request, *args, **kwargs):
        get_logger().info("ZendeskUserJWTMobileView GET")
        get_logger().info(str(request.GET))

    def post(self, request, *args, **kwargs):
        get_logger().info("ZendeskUserJWTMobileView POST")
        get_logger().info(str(request.POST))

        jwt_token = request.POST.get("user_token", "0")
        account = Account.objects.filter(id=int(jwt_token)).first()
        if not account:
            account = Owner.objects.filter(id=int(jwt_token)).first()

        if account:
            jwt_token = account.get_or_create_jwt_for_zendesk(ZENDESK_MOBILE_SECRET)

            get_logger().info("ZendeskUserJWTMobileView JWT SEND")
            get_logger().info(jwt_token)

            return JsonResponse({"jwt": jwt_token})
        else:
            return HttpResponse("User is not found", status=400)


class UpdateTokenView(APIView):
    def post(self, request):
        """
        old_token = request.data.get("token", None)
        if old_token:
            AccountSession.objects.filter(token=token)
        """
        return JsonResponse(status=200)


class AccountSubscriptionListView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        not_active = request.GET.get("not_active", False)
        active_state = True
        
        if (not_active):
            active_state = False

        subscription_qs = RpsSubscription.objects.filter(
            #started_at__lt = timezone.now(),
            #expired_at__gte = timezone.now(),
            active=active_state,
            account=request.account
        ).select_related('parking')

        serialized_subs = serializer(subscription_qs,
                                     include_attr=('id','name', 'description', 'sum', 'data', 'started_at',
                                                   'expired_at', 'duration', 'prolongation', 'unlimited',
                                                   'state', 'active', 'error_message',))
        for index, sub in enumerate(subscription_qs):
            serialized_subs[index]["parking"] = serializer(
                sub.parking, include_attr=('id', 'name', 'description'))

        response_dict = {
            "result":serialized_subs
        }
        return JsonResponse(response_dict, status=200)


class AccountSubscriptionView(LoginRequiredAPIView):
    def get(self, request, *args, **kwargs):
        try:
            sub = RpsSubscription.objects.select_related('parking').get(
                account=request.account,
                id=kwargs["pk"])
            result_dict = serializer(sub, include_attr=('id','name', 'description', 'sum', 'data', 'started_at',
                                                        'expired_at', 'duration', 'prolongation', 'unlimited',
                                                        'state', 'active', 'error_message',))
            result_dict["parking"] = serializer(
                    sub.parking, include_attr=('id', 'name', 'description'))
            return JsonResponse(result_dict, status=200)

        except ObjectDoesNotExist:
            pass

        e = ValidationException(
            ValidationException.RESOURCE_NOT_FOUND,
            "Your target subscription with order such id not found"
        )
        return JsonResponse(e.to_dict(), status=400)


class AccountSubscriptionSettingsView(LoginRequiredAPIView):

    def post(self, request, *args, **kwargs):
        prolong_status = request.data.get("prolong")
        if type(prolong_status) != bool:
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Key `prolong` should be boolean type")
            return JsonResponse(e.to_dict(), status=400)
        try:
            sub = RpsSubscription.objects.get(
                id=int(kwargs["pk"]),
                account=request.account
            )
            sub.prolongation = prolong_status
            sub.save()
            sub.check_prolong_payment()

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Your subscription with id %s does not exist" % int(kwargs["pk"]))
            return JsonResponse(e.to_dict(), status=400)

        return JsonResponse({}, status=200)


class ExternalLoginView(APIView):
    validator_class = ExternalLoginValidator

    def post(self, request):
        vendor_id = int(request.data["vendor_id"])
        external_user_id = str(request.data["external_user_id"])

        try:
            vendor = Vendor.objects.get(id=vendor_id)
            try:
                if not vendor.is_external_user(external_user_id):
                    e = AuthException(
                        AuthException.INVALID_EXTERNAL_USER,
                        "Remote user does not found")
                    return JsonResponse(e.to_dict(), status=400)

                account = Account.objects.get(
                    external_vendor_id=vendor_id,
                    external_id=external_user_id)

                account.login()
                session = account.get_session()
                return JsonResponse(
                    serializer(session, exclude_attr=("created_at",)))

            except Exception as e:
                e = AuthException(
                    AuthException.EXTERNAL_LOGIN_ERROR,
                    "Error at singing up external user | %s " % str(e))
                return JsonResponse(e.to_dict(), status=400)

        except ObjectDoesNotExist:
            e = ValidationException(
                ValidationException.RESOURCE_NOT_FOUND,
                "Vendor with id %d does not exist" % vendor_id)
            return JsonResponse(e.to_dict(), status=400)


class MockingExternalLoginView(SignedRequestAPIView):
    def post(self, request, *args, **kwargs):
        id = request.data["id"]
        if id == 'test_id':
            data = {
                "id": 'test_id',
                "phone": "+7(909)2335229",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com"
            }
            return JsonResponse(data, status=200)
        return JsonResponse({}, status=400)


class WriteUsersLogsView(APIView):
    validator_class = UsersLogValidator

    def post(self, request):
        user_id = int(request.data["user_id"])
        logs = request.data["logs"]

        elastic_log(ES_APP_BLUETOOTH_LOGS_INDEX_NAME, "Mobile app logs", {
           'logs': logs,
           'user_id': user_id
        })
        #
        # for item in logs:
        #     _id = item.pop("id")
        #     item["user_id"] = user_id
        #
        #     es_client.index(
        #         index=ES_APP_BLUETOOTH_LOGS_INDEX_NAME,
        #         id=_id,
        #         body=item
        #     )

        get_logger().info("Write user logs " + str(user_id))
        # get_logger().info(str(logs))
        get_logger().info("End user logs " + str(user_id))

        return JsonResponse({}, status=200)


