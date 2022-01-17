import base64
from pathlib import Path

import django
import os
import sys
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parkpass_backend.settings")
django.setup()

import openpyxl
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string

from parkpass_backend.settings import EMAIL_HOST_USER

from django.core.mail import get_connection, EmailMultiAlternatives

def send_mass_html_mail(datatuple, fail_silently=False, user=None, password=None,
                        connection=None):
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    """
    connection = connection or get_connection(
        username=user, password=password, fail_silently=fail_silently)
    messages = []
    for subject, text, html, from_email, recipient in datatuple:
        message = EmailMultiAlternatives(subject, text, from_email, recipient)
        message.attach_alternative(html, 'text/html')
        messages.append(message)
    return connection.send_messages(messages)


def main():
    xlsx_file = Path('emails/ios_users.xlsx')
    # xlsx_file = Path('emails/test_ios_users.xlsx')

    wb_obj = openpyxl.load_workbook(xlsx_file)
    emails = []
    # Read the active sheet:
    sheet = wb_obj.active
    # print(sheet)
    ri = 0
    for row in sheet.iter_rows():
        i = 0
        if ri:
            for cell in row:
                if i == 2:
                    if cell.value: emails.append(cell.value)
                i += 1
        ri += 1

    emails = ['brigadir@gmail.com'] # for test
    messages = []

    for email in emails:
        base64_email = None
        message = None
        try:
            base64_email = base64.b64encode(bytes(str(email), 'utf-8')).decode('utf-8')
            msg_html = render_to_string('emails/ios-template.html', {'email': base64_email})
            message = ('Участие в Beta-тестирвании ParkPass 3.0 для iOS', '', msg_html, EMAIL_HOST_USER, [email])
        except Exception as e:
            print('Не удалось сформировать сообщение для %s', email)
            print(e)

        if base64_email and message:
            messages.append(message)

    res = send_mass_html_mail(messages, fail_silently=False)
    print(res)

if __name__ == '__main__':
    main()
