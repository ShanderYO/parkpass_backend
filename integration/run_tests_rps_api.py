import unittest
from unittest.mock import patch, Mock
from datetime import datetime
import requests
from rps_integration import RPSService

# Замените на реальные данные для тестового RPS
TEST_RPS_DOMAIN = 'https://test-rps.com'
TEST_INTEGRATOR_ID = 'test_integrator_id'
TEST_TOKEN = 'test_token'

class TestRPSService(unittest.TestCase):
    def setUp(self):
        self.rps_parking = Mock()
        self.rps_parking.integrator_id = TEST_INTEGRATOR_ID
        self.rps_parking.token = TEST_TOKEN
        self.service = RPSService(self.rps_parking)

    @patch('requests.post')
    def test_purchase_subscription_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        user_id = '100000000000000001'
        subscription_id = '12345'
        amount = 5000
        ts_id = 'IdTS_rps'
        transaction_id = 'IdPerehoda'

        result = self.service.purchase_subscription(user_id, subscription_id, amount, ts_id, transaction_id)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_purchase_subscription_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        user_id = '100000000000000001'
        subscription_id = '12345'
        amount = 5000
        ts_id = 'IdTS_rps'
        transaction_id = 'IdPerehoda'

        result = self.service.purchase_subscription(user_id, subscription_id, amount, ts_id, transaction_id)
        self.assertEqual(result, 400)

    @patch('requests.get')
    def test_get_subscriptions_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'subscription_id': '123', 'name': 'Subscription 1'}]
        mock_get.return_value = mock_response

        result = self.service.get_subscriptions()
        self.assertEqual(result, [{'subscription_id': '123', 'name': 'Subscription 1'}])

    @patch('requests.get')
    def test_get_subscriptions_failure(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500  # Example of failure status code
        mock_get.return_value = mock_response

        result = self.service.get_subscriptions()
        self.assertIsNone(result)

    @patch('requests.post')
    def test_subscription_callback_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        subscription_id = '12345'
        expired_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = self.service.subscription_callback(subscription_id, expired_at)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_subscription_callback_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        subscription_id = '12345'
        expired_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = self.service.subscription_callback(subscription_id, expired_at)
        self.assertEqual(result, 400)

    @patch('requests.post')
    def test_entrance_permission_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.entrance_permission(eTicket, regularCustomerId)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_entrance_permission_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.entrance_permission(eTicket, regularCustomerId)
        self.assertEqual(result, 400)

    @patch('requests.post')
    def test_entrance_confirmation_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.entrance_confirmation(eTicket, regularCustomerId)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_entrance_confirmation_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.entrance_confirmation(eTicket, regularCustomerId)
        self.assertEqual(result, 400)

    @patch('requests.post')
    def test_exit_permission_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        deviceId = 1234
        qrNumber = 12398747126
        eTicket = '1946943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.exit_permission(deviceId, qrNumber, eTicket, regularCustomerId)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_exit_permission_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        deviceId = 1234
        qrNumber = 12398747126
        eTicket = '1946943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.exit_permission(deviceId, qrNumber, eTicket, regularCustomerId)
        self.assertEqual(result, 400)

    @patch('requests.post')
    def test_exit_confirmation_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        deviceId = 1234
        qrNumber = 12398747126
        eTicket = '1946943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.exit_confirmation(deviceId, qrNumber, eTicket, regularCustomerId)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_exit_confirmation_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        deviceId = 1234
        qrNumber = 12398747126
        eTicket = '1946943351102011010'
        regularCustomerId = '100001000000000001'

        result = self.service.exit_confirmation(deviceId, qrNumber, eTicket, regularCustomerId)
        self.assertEqual(result, 400)

    @patch('requests.post')
    def test_notify_payment_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'
        amount = 20000

        result = self.service.notify_payment(eTicket, regularCustomerId, amount)
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_notify_payment_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        eTicket = '1942943351102011010'
        regularCustomerId = '100001000000000001'
        amount = 20000

        result = self.service.notify_payment(eTicket, regularCustomerId, amount)
        self.assertEqual(result, 400)

if __name__ == '__main__':
    unittest.main()
