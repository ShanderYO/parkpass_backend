import collections
import hashlib
import json

import requests
from django.core.exceptions import ObjectDoesNotExist

from base.models import Terminal
from base.utils import get_logger
from parkpass import settings


class TinkoffApiException:
    TINKOFF_EXCEPTION_3DS_NOT_AUTH = [101]
    TINKOFF_EXCEPTION_DENIED_FROD_MONITOR = [102]
    TINKOFF_EXCEPTION_INVALID_CARD = [1006, 1014, 1012, 1033, 1054, 1082, 1091]
    TINKOFF_EXCEPTION_INVALID_REPEAT_LATER = [1013, 1030]
    TINKOFF_EXCEPTION_BANK_OPERATION_DENIED = [99, 1034, 1041, 1043, 1057, 1065, 1089]
    TINKOFF_EXCEPTION_MANY_MONEY = [1051]
    TINKOFF_EXCEPTION_INTERNAL_ERROR = [9999]


class TinkoffAPI():
    INIT = "https://securepay.tinkoff.ru/v2/Init"
    CONFIRM = "https://securepay.tinkoff.ru/v2/Confirm"
    CHARGE = "https://securepay.tinkoff.ru/v2/Charge"
    CANCEL = "https://securepay.tinkoff.ru/v2/Cancel"

    def __init__(self):
        try:
            terminal = Terminal.objects.get(is_selected=True)
        except ObjectDoesNotExist:
            terminal = Terminal.objects.create(
                terminal_key=settings.TINKOFF_TERMINAL_KEY,
                password=settings.TINKOFF_TERMINAL_PASSWORD
            )
        self.terminal_key = str(terminal.terminal_key)  # settings.TINKOFF_TERMINAL_KEY "1516954410942DEMO"
        self.password = str(terminal.password)  # settings.TINKOFF_TERMINAL_PASSWORD "dybcdp86npi8s9fv"

    def sync_call(self, method, body):
        body["TerminalKey"] = self.terminal_key
        body["Password"] = self.password

        ordered_data = collections.OrderedDict(sorted(body.items()))
        body["Token"] = self.get_token(ordered_data)

        return self.get_response(method, body)

    def get_token(self, params):
        concat_str = ""
        for key in params:
            concat_str += str(params[key])
        return hashlib.sha256(concat_str).hexdigest()

    def get_response(self, url, payload):
        connect_timeout = 2

        headers = {'Content-Type': 'application/json'}
        json_data = json.dumps(payload)
        get_logger().info('TinkoffAPI payload: ' + json_data)

        try:
            r = requests.post(url, data=json_data, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                result = r.json()
                return result

            except Exception as e:
                return None

        except requests.exceptions.MissingSchema as e:
            #print "Missing schema for request"
            return None

        except requests.exceptions.ConnectionError as e:
            #print "These aren't the domains we're looking for."
            return None

        except requests.exceptions.ConnectTimeout as e:
            #print "Too slow Mojo!"
            return None

        except requests.exceptions.ReadTimeout as e:
            #print "Waited too long between bytes."
            return None

        except requests.exceptions.HTTPError as e:
            #print "Server return 500."
            return None
