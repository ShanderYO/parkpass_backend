from django.core.exceptions import ObjectDoesNotExist
from base.exceptions import ValidationException
import asyncio
from aiogram_broadcaster import TextBroadcaster

BOT_TOKEN = '5394962244:AAFmxIl-sSjLnryKTR4V7pmYau1wetARztI'


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

#
# def send_message_by_valetapp_bot(message, company_id):
#     from owners.models import CompanyUser
#     async def run():
#
#         try:
#
#             users = CompanyUser.objects.filter(company_id=company_id, telegram_id__isnull=False)
#
#             if users:
#                 chats = []
#                 for user in users:
#                     chats.append(user.telegram_id)
#                 # Initialize a text broadcaster (you can directly pass a token)
#                 broadcaster = TextBroadcaster(chats, message, bot_token=BOT_TOKEN)
#
#                 # Run the broadcaster and close it afterwards
#                 try:
#                     await broadcaster.run()
#                 finally:
#                     await broadcaster.close_bot()
#
#         except Exception as e:
#             print(str(e))
#
#     asyncio.run(run())
