import datetime

import pytz
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from django.core.exceptions import ObjectDoesNotExist

from bots.telegram_valet_bot.utils.utils import get_parking_info
from parkings.models import Parking, ParkingValetTelegramChat
import aiogram.utils.markdown as fmt


class Process(StatesGroup):
    waiting_for_parking = State()


async def set_parking(message: types.Message, state: FSMContext):
    await state.finish()

    await Process.waiting_for_parking.set()

    await message.answer(
        "Привет, введите ключ вашей парковки, пожалуйста",
    )


async def parking_choosen(message: types.Message, state: FSMContext):
    parking_valet_key = message.text
    chat_id = message.chat.id
    if len(parking_valet_key) != 36:
        await message.answer(
            'Введен неверный ключ'
        )
        await state.finish()
        return

    if ParkingValetTelegramChat.objects.filter(valet_telegram_secret_key=parking_valet_key).exists():
        await message.answer(
            'Данный ключ уже использовался для установки парковки. Пожалуйста используйте новый ключ.'
        )
        await state.finish()
        return

    try:
        parking = Parking.objects.get(valet_telegram_secret_key=parking_valet_key)
        parking.set_valet_telegram_chat(chat_id)

    except ObjectDoesNotExist:
        await message.answer(
            'Парковка не найдена. 🤔'
        )
        await state.finish()
        return

    await message.answer('Парковка установлена! 🧡')

    await state.finish()


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(set_parking, commands="set_parking", state="*")
    dp.register_message_handler(parking_choosen, state=Process.waiting_for_parking)
