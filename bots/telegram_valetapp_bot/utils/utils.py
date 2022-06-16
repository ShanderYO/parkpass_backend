from django.core.exceptions import ObjectDoesNotExist
from base.exceptions import ValidationException
import asyncio
from aiogram_broadcaster import TextBroadcaster


def set_user_telegram_id(user_id, telegram_id):
    from owners.models import CompanyUser
    try:
        user = CompanyUser.objects.get(id=user_id)
        user.telegram_id = telegram_id
        user.save()

    except ObjectDoesNotExist:
        e = ValidationException(
            ValidationException.RESOURCE_NOT_FOUND,
            "User with id %s does not exist" % user_id
        )
        print(e.to_dict())
