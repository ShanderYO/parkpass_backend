# -*- coding: utf-8 -*-
import requests

from base.exceptions import NetworkException
from sms_gateway.base_provider import SMSBaseProvider


class SMSProviderUnisender(SMSBaseProvider):
    SEND_SMS_URL = "https://api.unisender.com/ru/api/sendSms"

    def __init__(self, conf):
        super(SMSProviderUnisender, self).__init__()
        self.api_key = conf["credentials"]["api_key"]
        self.sender = conf["sender_name"]

    def build_request(self):
        connect_timeout = 5
        url = self.SEND_SMS_URL + "?format=json&api_key=%s&phone=%s&sender=%s&text=%s" \
                                  % (self.api_key, self.phone, self.sender, self.message)
        return requests.get(url, timeout=(connect_timeout, 10.0))

    def send_sms(self, phone, message):
        self.phone = phone
        self.message = message
        result = self.send_by_request().json()

        if result and result.get(u"error", None):
            self.exception = NetworkException(
                NetworkException.SMD_GATEWAY_ERROR,
                result["error"]
            )


class SMSProviderBeeline(SMSBaseProvider):
    SEND_SMS_URL = "https://beeline.amega-inform.ru/sms_send/"

    def __init__(self, conf):
        super(SMSProviderBeeline, self).__init__()
        self.api_user = conf["credentials"]["user"]
        self.api_password = conf["credentials"]["password"]
        self.sender = conf["sender_name"]

    def build_request(self):
        connect_timeout = 5
        payload = {
            "user": self.api_user,
            "pass": self.api_password,
            "action": "post_sms",
            "message": self.message,
            "target": "+%s" % self.phone
        }
        return requests.post(
            SMSProviderBeeline.SEND_SMS_URL, data=payload, timeout=(connect_timeout, 10.0))

    def send_sms(self, phone, message):
        self.phone = phone
        self.message = message
        result = self.send_by_request().json()

        if result and result.get(u"error", None):
            self.exception = NetworkException(
                NetworkException.SMD_GATEWAY_ERROR,
                result["error"]
            )