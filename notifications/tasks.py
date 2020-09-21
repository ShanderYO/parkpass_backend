import json
import logging

from notifications.models import AccountDevice
from parkpass_backend.celery import app


@app.task()
def send_broadcast_message(title, body, data):
    logging.info("Send broadcast push message")
    qs = AccountDevice.objects.filter(active=True)
    for account_device in qs:
        if title and body:
            if data:
                d = json.loads(data)
                account_device.send_message(title=title, body=body, data=d)
            else:
                account_device.send_message(title=title, body=body)
