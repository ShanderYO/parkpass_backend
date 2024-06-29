import pytest

from django.core.management import call_command


@pytest.fixture(scope='function')
def django_db_reset(request, django_db_setup, django_db_blocker):
    # Заблокируйте доступ к базе данных, чтобы избежать ошибок внутри транзакций
    with django_db_blocker.unblock():
        # Используйте команду flush для удаления данных из базы данных
        # и команду migrate для применения миграций
        call_command('flush', interactive=False)
        call_command('migrate')
