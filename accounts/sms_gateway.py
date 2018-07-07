import requests

from base.exceptions import NetworkException
from parkpass import settings


class SMSGateway(object):
    SEND_SMS_URL = "https://api.unisender.com/ru/api/sendSms"

    def __init__(self):
        self.api_key = settings.SMS_GATEWAY_API_KEY
        self.sender = settings.SMS_SENDER_NAME
        self.exception = None

    def send_sms(self, phone, code):
        formatted_phone = self._get_phone_format(phone)
        content = self._get_sms_content(code)

        connect_timeout = 5
        url = self.SEND_SMS_URL + "?format=json&api_key=%s&phone=%s&sender=%s&text=%s" \
                                % (self.api_key, formatted_phone, self.sender, content)
        try:
            r = requests.get(url, timeout=(connect_timeout, 10.0))
            result = r.json()
            if result.get(u"error", None):
                self.exception = NetworkException(
                    NetworkException.SMD_GATEWAY_ERROR,
                    result["error"]
                )

        except requests.exceptions.ConnectionError as e:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Sms gateway not found"
            )

        except requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Timeout error"
            )

        except requests.exceptions.HTTPError as e:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Sms gateway server error"
            )

        except requests.exceptions.RequestException:
            self.exception = NetworkException(
                NetworkException.SMS_GATEWAY_NOT_AVAILABLE,
                "Unknown exception"
            )

    def _get_phone_format(self, phone):
        return phone.replace('+', '').replace('(', '').replace(')', '').replace(' ', '')

    def _get_sms_content(self, code):
        return "Secret+code+for+login+%s" % code

