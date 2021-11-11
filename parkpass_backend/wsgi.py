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

if not 'runserver' in sys.argv:
    os.system("nohup sh /app/TelegramPaymentBot/bot.sh 0<&- &> telegram_bot.log.file &")