import datetime

import pytz
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from bots.telegram_valetapp_bot.utils.utils import set_user_telegram_id
from parkings.models import Parking
import aiogram.utils.markdown as fmt

class PaymentProcess(StatesGroup):
    waiting_for_parking = State()
    waiting_for_card = State()

async def set_parking(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    parking_id = call['data'][8:]
    await call.message.answer(
        'Введите номер карты / билета / жетона'
    )
    await state.update_data(parking_id=parking_id)
    await PaymentProcess.waiting_for_parking.set()
    await call.answer()


async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    keyboard = types.InlineKeyboardMarkup(row_width=3)

    text_from_message = message.text.replace('/start ', '')

    if len(text_from_message) == 38:
        user_id = text_from_message[12:14]
        telegram_id = message.chat.id
        set_user_telegram_id(user_id, telegram_id)

    await message.answer(
        "Телеграмм уведомления подключены",
        reply_markup=keyboard
    )

async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())

def register_handlers_common(dp: Dispatcher):

    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_cancel, commands="cancel", state="*")
    dp.register_message_handler(cmd_cancel, Text(equals="отмена", ignore_case=True), state="*")

    dp.register_callback_query_handler(set_parking, Text(startswith="parking_"), state="*")
