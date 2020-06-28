from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.six import text_type

# Header encoding (see RFC5987)
from accounts.models import AccountSession, Account
from jwtauth.models import Groups, TokenTypes, Session
from jwtauth.utils import parse_jwt
from base.utils import datetime_from_unix_timestamp_tz
from control.models import AdminSession, Admin
from owners.models import OwnerSession, Owner
from vendors.models import VendorSession, Vendor

HTTP_HEADER_ENCODING = 'iso-8859-1'

account = (b'token', AccountSession)
vendor = (b'vendor', VendorSession)
owner = (b'owner', OwnerSession)
admin = (b'admin', AdminSession)


def get_authorization_header(self, request):
    authorization = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(authorization, text_type):
        authorization = authorization.encode(HTTP_HEADER_ENCODING)
    return authorization


class ComplexAuthenticationMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.is_jwt_authorize(request):
            print("is_jwt_authorize")
            middleware = JWTTokenAuthenticationMiddleware(self.get_response)
            return middleware(request)

        else:
            print("is_old_authorize")
            middleware = TokenAuthenticationMiddleware(self.get_response)
            return middleware(request)

    def is_jwt_authorize(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'bearer':
            return False
        return True


class JWTTokenAuthenticationMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("JWTTokenAuthenticationMiddleware process request")
        request.account = SimpleLazyObject(lambda: self.get_jwt_account(request, Groups.BASIC))
        request.vendor = SimpleLazyObject(lambda: self.get_jwt_account(request, Groups.VENDOR))
        request.owner = SimpleLazyObject(lambda: self.get_jwt_account(request, Groups.OWNER))
        request.admin = SimpleLazyObject(lambda: self.get_jwt_account(request, Groups.ADMIN))

        return self.get_response(request)

    def get_jwt_account(self, request, group):
        access_token = self.get_access_token(request)
        claims = parse_jwt(access_token)

        if claims:
            print(claims)
            expires_at = int(claims.get("expires_at", 0))
            groups = int(claims.get("groups", 0))
            type = int(claims.get("type", -1))
            user_id = int(claims.get("user_id", 0))

            # If token is expired
            if datetime_from_unix_timestamp_tz(expires_at) <= timezone.now():
                return None

            if TokenTypes.MOBILE == type:
                sessions = Session.objects.filter(
                    temp_user_id=user_id,
                    type=TokenTypes.MOBILE,
                    last_expired_access_token = expires_at
                ).order_by('-last_expired_access_token')

                active_session = sessions.first()

                if not active_session:
                    return None

                if active_session.last_expired_access_token != expires_at:
                    return None

            if group == Groups.BASIC:
                return Account.objects.filter(id=user_id).first()

            if group == Groups.VENDOR and groups & group > 0:
                return Vendor.objects.filter(id=user_id).first()

            if group == Groups.OWNER and groups & group > 0:
                return Owner.objects.filter(id=user_id).first()

            if group == Groups.ADMIN and groups & group > 0:
                return Admin.objects.filter(id=user_id).first()

        return None

    def get_access_token(self, request):
        auth = self.get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'bearer':
            return None

        if len(auth) == 1 or len(auth) > 2:
            return None

        return auth[1].decode()

    def get_authorization_header(self, request):
        authorization = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(authorization, text_type):
            authorization = authorization.encode(HTTP_HEADER_ENCODING)
        return authorization


class TokenAuthenticationMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("TokenAuthenticationMiddleware process request")
        request.account = SimpleLazyObject(lambda: get_account(request, account))
        request.vendor = SimpleLazyObject(lambda: get_account(request, vendor))
        request.owner = SimpleLazyObject(lambda: get_account(request, owner))
        request.admin = SimpleLazyObject(lambda: get_account(request, admin))

        return self.get_response(request)


def get_authorization_header(request):
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, text_type):
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


def get_account(request, ac_type):
    auth = get_authorization_header(request).split()

    if not auth or auth[0].lower() != ac_type[0]:
        return None

    if len(auth) == 1:
        return None

    if len(auth) > 2:
        return None
    try:
        token = auth[1].decode()
    except Exception:
        return None

    return ac_type[1].get_account_by_token(token)