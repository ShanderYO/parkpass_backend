from django.utils.functional import SimpleLazyObject
from django.utils.six import text_type

# Header encoding (see RFC5987)
from accounts.models import AccountSession
from control.models import AdminSession
from owners.models import OwnerSession
from vendors.models import VendorSession

HTTP_HEADER_ENCODING = 'iso-8859-1'

account = (b'token', AccountSession)
vendor = (b'vendor', VendorSession)
owner = (b'owner', OwnerSession)
admin = (b'admin', AdminSession)


class TokenAuthenticationMiddleware(object):
    def process_request(self, request):
        request.account = SimpleLazyObject(lambda: get_account(request, account))
        request.vendor = SimpleLazyObject(lambda: get_account(request, vendor))
        request.owner = SimpleLazyObject(lambda: get_account(request, owner))
        request.admin = SimpleLazyObject(lambda: get_account(request, admin))


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
    except UnicodeError:
        return None

    return ac_type[1].get_account_by_token(token)