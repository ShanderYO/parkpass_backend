import collections
import hashlib
import json
import os
from base64 import b64encode, b64decode

import requests
from django.core.exceptions import ObjectDoesNotExist

from base.models import Terminal
from base.utils import get_logger, elastic_log
from parkpass_backend import settings
from parkpass_backend.settings import ES_APP_PAYMENTS_LOGS_INDEX_NAME


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
    OFD_AUTH_URL = "https://org.1-ofd.ru/api/user/login"
    OFD_GET_CHECK_URL = "https://org.1-ofd.ru/api/ticket/"

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

    def get_check_url (self, ecr_reg_number, fn_number, fiscal_document_number):
        get_logger().info('get tinkoff check url %s %s %s' % (ecr_reg_number, fn_number, fiscal_document_number))

        auth = requests.post(self.OFD_AUTH_URL, data=json.dumps({
            "login": settings.TINKOFF_ODF_LOGIN,
            "password": settings.TINKOFF_ODF_PASSWORD
        }), headers={'Content-Type': 'application/json'})

        transaction_id = '%s_%s_%s' % (ecr_reg_number, fn_number, fiscal_document_number)
        r = requests.get(self.OFD_GET_CHECK_URL + transaction_id, cookies=auth.cookies)

        if r.status_code == 200:
            result = r.json()
            return result
        return None


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

    # TOKEN_URL = "https://testoauth.homebank.kz/epay2/oauth2/token"
    # AUTHORIZED_URL = "https://testepay.homebank.kz/api/payments/cards/auth"
    # CONFIRMED_URL = "https://testepay.homebank.kz/api/operation/%s/charge"
    # CANCEL_URL = "https://testepay.homebank.kz/api/operation/%s/cancel"


    TOKEN_URL = "https://epay-oauth.homebank.kz/oauth2/token"
    AUTHORIZED_URL = "https://epay-api.homebank.kz/payments/cards/auth"
    CONFIRMED_URL = "https://epay-api.homebank.kz/operation/%s/charge"
    CANCEL_URL = "https://epay-api.homebank.kz/operation/%s/cancel"


    token = None

    def get_token(self, params={}, scope="webapi"):
        get_logger().info("Get HomeBank token")
        payload = {
            "grant_type": "client_credentials",
            "scope": scope,
            "client_id": settings.HOMEBANK_CLIENT_ID,
            "client_secret": settings.HOMEBANK_CLIENT_SECRET,
        }
        payload.update(params)
        r = self.get_response(self.TOKEN_URL, payload)

        if r['access_token']:
            self.token = r['access_token']
            return True

        return None

    def cancel_payment(self, payment_id):
        get_logger().info("cancel payment")

        token = self.get_token()
        if not token:
            get_logger().error("No token for request")
            return None

        headers = {'Authorization': 'bearer ' + self.token}
        r = requests.post(self.CANCEL_URL % payment_id, headers=headers)
        if r.status_code == 200:
            get_logger().info("cancel success")
            return True

        return None


    def authorize(self, data):
        params = {
            'invoiceID': data['invoiceId'],
            'amount': data['amount'],
            "terminal": data['terminalId'],
            'currency': 'KZT',
            'postLink': '',
            'failurePostLink': '',
        }
        get_logger().info("HomeBank make payment")

        token = self.get_token(params=params, scope='payment')
        if not token:
            get_logger().error("No token for request")
            return None


        get_logger().info(params)

        return self.get_response(self.AUTHORIZED_URL, data)

    def confirm(self, id):
        get_logger().info("HomeBank confirm payment")

        token = self.get_token()
        if not token:
            get_logger().error("No token for request")
            return None

        headers = {'Authorization': 'bearer ' + self.token}
        r = requests.post(self.CONFIRMED_URL % id, headers=headers)
        if r.status_code == 200:
            get_logger().info("confirm success")
            return True

        return None

    def get_response(self, url, payload={}):
        connect_timeout = 5
        headers = {}
        json_data = payload

        if 'paymentType' in payload:
            json_data = json.dumps(payload)
            headers['Content-Type'] = 'application/json'

        if self.token:
            headers['Authorization'] = 'bearer ' + self.token

        # elastic_log(ES_APP_PAYMENTS_LOGS_INDEX_NAME, "Make request to HomeBank", json_data)
        log_data = payload.copy()

        get_logger().info('HomeBank payload: ' + json.dumps(log_data))


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

class HomeBankOdfAPI():
    TOKEN_URL = "https://kkm.webkassa.kz/api/Authorize"
    GET_SHIFTS_URL = "https://kkm.webkassa.kz/api/Cashbox/ShiftHistory"
    CREATE_CHECK = "https://kkm.webkassa.kz/api/Check"

    token = None
    shift = None

    def get_token(self):
        get_logger().info("Get HomeBank ODF token")
        payload = {
            "Login": settings.HOMEBANK_ODF_LOGIN,
            "Password": settings.HOMEBANK_ODF_PASSWORD,
        }
        r = self.get_response(self.TOKEN_URL, payload)

        if r and r['Data'] and r['Data']['Token']:
            self.token = r['Data']['Token']
            return True

        return None


    def get_shifts(self):

        get_logger().info("Get HomeBank ODF shifts")

        payload = {
            "Token": self.token,
            "CashboxUniqueNumber": settings.HOMEBANK_ODF_KASSA_ID,
            "Skip": 0,
            "Take": 50
        }
        get_logger().info("HomeBank get shifts request")

        r = self.get_response(self.GET_SHIFTS_URL, payload)

        if r and r['Data'] and r['Data']['Shifts']:
            self.shift = r['Data']['Shifts'][0]['ShiftNumber']
            return True

        return None


    def create_check(self, order, payment):

        get_logger().info("HomeBank ODF creating check")

        if not self.get_token():
            get_logger().error("No token for request")
            return None

        if not payment:
            get_logger().info("HomeBank ODF Error: no payment")
            return None

        # if not self.get_shifts():
        #     get_logger().error("No shift for request")
        #     return None

        receipt_data = json.loads(payment.receipt_data)

        payload = {
            "Token": self.token,
            "CashboxUniqueNumber": settings.HOMEBANK_ODF_KASSA_ID,
            "OperationType": 2,
            "Positions": [
                {
                    "Count": 1,
                    "Price": int(order.sum),
                    "Taxpercent": 0,
                    "Tax": 0,
                    "TaxType": 0,
                    "PositionName": receipt_data['description'],
                    "UnitCode": 5114
                }
            ],
            "Payments": [
                {
                    "Sum": int(order.sum),
                    "PaymentType": 1
                }
            ],
            "Change": 0,
            "RoundType": 2,
            "ExternalCheckNumber": receipt_data['invoiceId'],
            # "CustomerEmail": "lokkomokko1@gmail.com"
        }

        check = self.get_response(self.CREATE_CHECK, payload)

        if not check:
            get_logger().info("Homebank ODF broke")
            return None

        return {
            "check_number": check["Data"]["CheckNumber"],
            "shift_number": check["Data"]["ShiftNumber"],
            "sum": order.sum,
            "date_time_string": check["Data"]["DateTime"],
            "address": check["Data"]["Cashbox"]["Address"],
            "ofd_name": check["Data"]["Cashbox"]["Ofd"]["Name"],
            "identity_number": check["Data"]["Cashbox"]["IdentityNumber"],
            "registration_number": check["Data"]["Cashbox"]["RegistrationNumber"],
            "unique_number": check["Data"]["Cashbox"]["UniqueNumber"],
            "ticket_url": check["Data"]["TicketUrl"],
        }




    def get_response(self, url, payload):
        connect_timeout = 5
        headers = {}
        json_data = payload

        # get_logger().info('HomeBank ODF payload: ' + json.dumps(json_data))

        try:
            r = requests.post(url, json=json_data, headers=headers,
                              timeout=(connect_timeout, 5.0))
            try:
                get_logger().info("Init odf status code %s" % r.status_code)
                if r.status_code != 200:
                    get_logger().info("%s", r.content)
                result = r.json()
                if "Errors" in result:
                    get_logger().info("requests for homebank odf catch error: " + json.dumps(result))
                    return None
                return result

            except Exception as e:
                get_logger().info(e)
                return None

        except requests.exceptions.MissingSchema as e:
            get_logger().info("Missing schema for request error")
            get_logger().info(e)
            return None

        except requests.exceptions.ConnectionError as e:
            get_logger().info("requests.exceptions.ConnectionError")
            get_logger().info(e)
            return None

        except requests.exceptions.ReadTimeout as e:
            get_logger().info("Waited too long between bytes error")
            get_logger().info(e)
            return None

        except requests.exceptions.HTTPError as e:
            get_logger().info("requests.exceptions.HTTPError")
            get_logger().info(e)
            return None