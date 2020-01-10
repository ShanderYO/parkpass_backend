import functools
from datetime import timedelta

import requests
from django.utils import timezone

from payments.models import TinkoffSession


def check_tinkoff_token(f):
    @functools.wraps
    def func(*args, **kwargs):
        return f()
    return func

class WithdrawAPI():
    UPDATE_TOKEN = "secure/token"
    LOGOUT = ""

    def __init__(self):
        self.active_session = TinkoffSession.objects.all().order_by('-created_at').first()

    def update_token(self):
        body = self.active_session.build_update_token_body()
        url = self.build_url(WithdrawAPI.UPDATE_TOKEN)
        try:
            res = requests.post(url, body)
            print(res.content)

            if res.status_code == 200:
                json_data = res.json()

                refresh_token = json_data["access_token"]
                access_token = json_data["access_token"]
                expires_in = timezone.now() + timedelta(seconds=int(json_data["expires_in"]))

                self.active_session = TinkoffSession.objects.create(
                    refresh_token=refresh_token,
                    access_token=access_token,
                    expires_in=expires_in,
                )

            # id_token ????

        except Exception as e:
            print(str(e))

    def get_requests(self):
        pass
