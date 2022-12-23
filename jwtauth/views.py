# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

# Create your views here.
from django.utils import timezone

from base.models import Country
from dss.Serializer import serializer

from accounts.models import Account
from accounts.sms_gateway import sms_sender
from accounts.validators import LoginParamValidator, NewConfirmLoginParamValidator, \
    EmailAndPasswordValidator, UpdateTokensValidator
from .models import Session, TokenTypes, Groups
from .utils import parse_jwt
from base.exceptions import AuthException
from base.utils import clear_phone
from base.views import APIView, LoginRequiredAPIView


class PhoneLoginView(APIView):
    validator_class = LoginParamValidator

    def post(self, request):
        phone = clear_phone(request.data["phone"])
        country_id = request.data.get("country_id", None)

        success_status = 200

        if Account.objects.filter(phone=phone).exists():
            account = Account.objects.get(phone=phone)
        else:
            account = Account(phone=phone)
            success_status = 201
            # Временный блок
            JsonResponse({}, status=201)
            

        if country_id:
            country = Country.objects.get(id=country_id)
            if country:
                account.country = country
        account.sms_verified = False
        account.create_sms_code(stub=(phone == "77891234560"))
        account.save()

        if phone == "77891234560":
            return JsonResponse({}, status=200)

        sms_sender.send_message(account.phone,
                                u"Код подтверждения %s" % (account.sms_code,))
        if sms_sender.exception:
            error_dict = sms_sender.exception.to_dict()
            sms_sender.exception = None
            return JsonResponse(error_dict, status=400)

        return JsonResponse({}, status=success_status)


class ConfirmPhoneLoginView(APIView):
    validator_class = NewConfirmLoginParamValidator

    def post(self, request):
        phone = clear_phone(request.data["phone"])
        sms_code = request.data["sms_code"]
        try:
            user = Account.objects.get(phone=phone, sms_code=sms_code)
            # Delete sessions
            Session.objects.filter(type=TokenTypes.MOBILE, temp_user_id=user.id).delete()
            session, created = Session.objects.get_or_create(
                type=TokenTypes.MOBILE,
                temp_user_id=user.id
            )
            if not session.is_valid():
                # Prolong session
                session.expires_at = None
                session.save()

            user.sms_verified = True
            user.save()

            response_dict = serializer(session, include_attr=("refresh_token", 'expires_at',))
            response_dict["access_token"] = session.update_access_token(group=Groups.BASIC)
            return JsonResponse(response_dict)

        except ObjectDoesNotExist:
            e = AuthException(
                AuthException.NOT_FOUND_CODE,
                "Account with pending sms-code for phone is not found")
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
                session = Session.objects.create(
                    #user=account,
                    type=TokenTypes.WEB,
                    temp_user_id=account.id
                )
                access_token = session.update_access_token(group=Groups.BASIC)
                response_dict = serializer(session, include_attr=("refresh_token", 'expires_at',))
                response_dict["access_token"] = access_token
                return JsonResponse(response_dict)

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
        Session.objects.filter(
            temp_user_id=request.account.id
        ).delete()
        return JsonResponse({}, status=200)


class UpdateTokensView(APIView):
    validator_class = UpdateTokensValidator

    def post(self, request):
        access_token = request.data["access_token"]
        refresh_token = request.data["refresh_token"]
        is_company_user = request.data.get("is_company_user", None)


        access_claims = parse_jwt(access_token)
        refresh_claims = parse_jwt(refresh_token)

        group = Groups.BASIC
        if is_company_user:
            group = Groups.COMPANY_USER

        if not access_claims:
            e = AuthException(
                AuthException.INVALID_TOKEN_FORMAT,
                "Invalid access_token"
            )
            return JsonResponse(e.to_dict(), status=400)

        if not refresh_claims:
            e = AuthException(
                AuthException.INVALID_TOKEN_FORMAT,
                "Invalid refresh_token"
            )
            return JsonResponse(e.to_dict(), status=400)

        session = Session.objects.filter(refresh_token=refresh_token).first()
        if not session:
            e = AuthException(
                AuthException.INVALID_SESSION,
                "Session for user does not exist. Login is required"
            )
            return JsonResponse(e.to_dict(), status=400)



        response_dict = serializer(session, include_attr=("refresh_token", 'expires_at',))
        response_dict["access_token"] = session.update_access_token(group=group)

        return JsonResponse(response_dict, status=200)

# TODO delete
class ReplaceTokensView(LoginRequiredAPIView):
    def post(self, request, *args, **kwargs):
        session, created = Session.objects.get_or_create(
            type=TokenTypes.MOBILE,
            temp_user_id=request.account.id
        )
        response_dict = serializer(session, include_attr=("refresh_token", 'expires_at',))
        response_dict["access_token"] = session.update_access_token(group=Groups.BASIC)
        return JsonResponse(response_dict)
