import pytest
from django.core.management import call_command
from django.db import connection

@pytest.fixture(scope="function", autouse=True)
def django_db_reset(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Полный flush базы
        call_command("flush", interactive=False)
        # Жёсткий сброс sequence
        reset_sequences()

def reset_sequences():
    tables = [
        "accounts_account",
        "owners_owner",
        "owners_company",
        "parkings_parking",
        "payments_order",
        "payments_tinkoffpayment",
        "parkings_parkingsession",
    ]
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT pg_get_serial_sequence('\"{table}\"', 'id')")
            seq = cursor.fetchone()[0]
            if seq:
                cursor.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
