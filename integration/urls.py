from django.urls import path
from . import views

urlpatterns = [
    path('token', views.TokenIntegrationView.as_view(), name='token_integration'),
]
