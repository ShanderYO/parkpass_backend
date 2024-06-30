# your_app/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

class TokenIntegrationView(APIView):
    @extend_schema(
        responses={200: 'Токен успешно получен'}
    )
    def post(self, request, *args, **kwargs):
        # Ваша логика
        return Response({"token": "example_token"}, status=status.HTTP_200_OK)
