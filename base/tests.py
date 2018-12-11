from django.test import TestCase, Client

from base.models import NotifyIssue


class Notify(TestCase):

    def test_valid_phone(self):
        URL = '/api/v1/notify/'
        phones = {
            "8(999)444-44-44",
            "89991234567",
            "7(914)4137488"
        }
        for phone in phones:
            Client().post(URL, '{"phone": "%s"}' % phone, content_type='application/json')
            notify = NotifyIssue.objects.get(phone=phone)
            self.assertEqual(notify.phone, phone)
            notify.delete()

    def test_invalid_phone(self):
        URL = '/api/v1/notify/'
        phones = {
            "8(99444-44-44",
            "8999123abc7",
            "7(914)413748823"
        }
        for phone in phones:
            response = Client().post(URL, '{"phone": "%s"}' % phone, content_type='application/json')
            self.assertEqual(response.status_code, 400)
