"""
WSGI config for parkpass_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parkpass_backend.settings')

application = get_wsgi_application()

if not 'runserver' in sys.argv and os.environ.get("PROD","0") == "1":
    os.system("nohup sh /app/bots/telegram_payment_bot/bot.sh 0<&- &> telegram_bot.log.file &")

if not 'runserver' in sys.argv:
    os.system("nohup sh /app/bots/telegram_valetapp_bot/bot.sh 0<&- &> telegram_valetapp_bot.log.file &")

if not 'runserver' in sys.argv:
    os.system("nohup sh /app/bots/telegram_valet_bot/bot.sh 0<&- &> telegram_valet_bot.log.file &")