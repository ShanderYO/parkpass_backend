import collections
import hashlib
import json
import os
from base64 import b64encode, b64decode

import requests
from Crypto.Cipher import PKCS1_OAEP
from django.core.exceptions import ObjectDoesNotExist

from base.models import Terminal
from base.utils import get_logger, elastic_log
from parkpass_backend import settings
from parkpass_backend.settings import ES_APP_PAYMENTS_LOGS_INDEX_NAME
import Crypto
from Crypto.PublicKey import RSA

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

    def __init__(self, with_terminal=None):
        try:
            if with_terminal:
                terminal = Terminal.objects.get(name=with_terminal)
            else:
                terminal = Terminal.objects.get(is_selected=True)

        except ObjectDoesNotExist:
            terminal = Terminal.objects.create(
                terminal_key=settings.TINKOFF_TERMINAL_KEY,
                password=settings.TINKOFF_TERMINAL_PASSWORD,
                is_selected=True,
            )
        self.terminal_key = str(terminal.terminal_key)
        self.password = str(terminal.password)

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
        return hashlib.sha256(concat_str.encode('utf-8')).hexdigest()

    def get_response(self, url, payload):
        connect_timeout = 2

        headers = {'Content-Type': 'application/json'}
        json_data = json.dumps(payload)

        elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Make request to Tinkoff", json_data)
        get_logger().info('TinkoffAPI payload: ' + json_data)

        try:
            r = requests.post(url, data=json_data, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                get_logger().info("Init status code %s" % r.status_code)
                elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                            "Tinkoff response status %s" % str(r.status_code),
                            r.content)
                if r.status_code != 200:
                    get_logger().info("%s", r.content)
                result = r.json()
                return result

            except Exception as e:
                elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                            "Tinkoff invoke error", str(e))
                get_logger().info(e)
                return None

        except requests.exceptions.MissingSchema as e:
            elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                        "Tinkoff invoke error", str(e))
            get_logger().info("Missing schema for request error")
            get_logger().info(e)
            return None

        except requests.exceptions.ConnectionError as e:
            elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                        "Tinkoff invoke error", str(e))
            get_logger().info("requests.exceptions.ConnectionError")
            get_logger().info(e)
            return None

        except requests.exceptions.ConnectTimeout as e:
            elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                        "Tinkoff invoke error", str(e))
            get_logger().info("requests.exceptions.ConnectTimeout")
            get_logger().info(e)
            return None

        except requests.exceptions.ReadTimeout as e:
            elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                        "Tinkoff invoke error", str(e))
            get_logger().info("Waited too long between bytes error")
            get_logger().info(e)
            return None

        except requests.exceptions.HTTPError as e:
            elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                        "Tinkoff invoke error", str(e))
            get_logger().info("requests.exceptions.HTTPError")
            get_logger().info(e)
            return None


class HomeBankAPI():
    TOKEN_URL = "https://testoauth.homebank.kz/epay2/oauth2/token"
    PAYMENT_URL = "https://testepay.homebank.kz/api/payments/cards/auth"

    token = None

    def get_token(self, params, scope="webapi"):
        get_logger().info("Get HomeBank token")
        payload = {
            "grant_type": "client_credentials",
            "scope": scope,
            "client_id": settings.HOMEBANK_CLIENT_ID,
            "client_secret": settings.HOMEBANK_CLIENT_SECRET,
        }
        r = self.get_response(self.TOKEN_URL, payload)

        if r['access_token']:
            self.token = r['access_token']
            return True

        return None

    def cancel_payment(self, payment_id):
        token = self.get_token()
        if not token:
            get_logger().error("No token for request")
            return None

        return self.get_response('https://testoauth.homebank.kz/operation/%s/cancel' % payment_id, {})

    def pay(self, data):
        params = {
            'invoiceID': data['invoiceID'],
            'amount': data['amount'],
            "terminal": data['terminal'],
            'currency': 'KZT',
            'postLink': '',
            'failurePostLink': '',
            'description': data['description']
        }

        token = self.get_token(params, 'payment')
        if not token:
            get_logger().error("No token for request")
            return None

        return self.get_response(self.PAY_URL, data)


    def get_response(self, url, payload):
        connect_timeout = 5

        json_data = payload

        headers = {}

        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
            print(self.token)

        # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Make request to HomeBank", json_data)
        log_data = json_data.copy()
        log_data.pop('cryptogram', None)
        get_logger().info('HomeBank payload: ' + json.dumps(log_data))

        if 'cryptogram' in json_data:
            json_data = json.dumps(json_data)
            print(json_data)
            print('Bearer ' + self.token)

        try:
            r = requests.post(url, data=json_data, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                get_logger().info("Init status code %s" % r.status_code)
                # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                #             "HomeBank response status %s" % str(r.status_code),
                #             r.content)
                if r.status_code != 200:
                    get_logger().info("%s", r.content)
                result = r.json()
                return result

            except Exception as e:
                # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
                #             "HomeBank invoke error", str(e))
                get_logger().info(e)
                return None

        except requests.exceptions.MissingSchema as e:
            # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            #             "HomeBank invoke error", str(e))
            get_logger().info("Missing schema for request error")
            get_logger().info(e)
            return None

        except requests.exceptions.ConnectionError as e:
            # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            #             "HomeBank invoke error", str(e))
            get_logger().info("requests.exceptions.ConnectionError")
            get_logger().info(e)
            return None

        except requests.exceptions.ReadTimeout as e:
            # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            #             "HomeBank invoke error", str(e))
            get_logger().info("Waited too long between bytes error")
            get_logger().info(e)
            return None

        except requests.exceptions.HTTPError as e:
            # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME,
            #             "HomeBank invoke error", str(e))
            get_logger().info("requests.exceptions.HTTPError")
            get_logger().info(e)
            return None
