from django.utils.functional import SimpleLazyObject
from django.utils.six import text_type

# Header encoding (see RFC5987)
from accounts.models import AccountSession
from vendors.models import VendorSession

HTTP_HEADER_ENCODING = 'iso-8859-1'


class TokenAuthenticationMiddleware(object):
    def process_request(self, request):
        request.vendor = SimpleLazyObject(lambda: get_vendor(request))
        request.account = SimpleLazyObject(lambda: get_account(request))


def get_authorization_header(request):
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, text_type):
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


def get_vendor(request):
    auth = get_authorization_header(request).split()

    if not auth or auth[0].lower() != b'vendor':
        return None

    if len(auth) == 1:
        return None

    if len(auth) > 2:
        return None
    try:
        token = auth[1].decode()
    except UnicodeError:
        return None

    return VendorSession.get_account_by_token(token)


def get_account(request):
    auth = get_authorization_header(request).split()

    if not auth or auth[0].lower() != b'token':
        return None

    if len(auth) == 1:
        return None

    if len(auth) > 2:
        return None
    try:
        token = auth[1].decode()
    except UnicodeError:
        return None

    return AccountSession.get_account_by_token(token)