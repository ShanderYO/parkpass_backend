import pytest
from django.urls import reverse
from django.test import Client

@pytest.mark.django_db
def test_token_integration_view():
    client = Client()
    url = reverse('token_integration')
    response = client.post(url)

    assert response.status_code == 200
    assert response.json() == {
        'status': 'success',
        'message': 'Token integration hook added successfully.'
    }
