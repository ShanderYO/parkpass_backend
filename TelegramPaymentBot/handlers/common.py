import datetime

import pytz
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from TelegramPaymentBot.utils.utils import get_parking_info
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

async def parking_choosen(message: types.Message, state: FSMContext):
    card_id = fmt.quote_html(message.text)
    if not card_id.isdigit():
        await message.answer("Пожалуйста, введите корректный номер")
        return
    await state.update_data(card_id=card_id)

    user_data = await state.get_data()
    result = get_parking_info(user_data['card_id'], user_data['parking_id'])
    # result = get_parking_info(3270385573, 106)
    if result['status'] == 'error':
        await message.answer('<b>Ошибка</b> \n\n%s' % result['message'])
        return

    mins = (result['data']['duration'] % 3600) // 60
    hours = (result['data']['duration'] % 86400) // 3600
    days = (result['data']['duration'] % 2592000) // 86400

    duration = "%sд. %sч. %sм." % (days, hours, mins)

    entered_at = datetime.datetime.fromtimestamp(result['data']['entered_at']/1000.0, pytz.timezone('Europe/Moscow')).strftime('%d.%m.%Y в %H:%M')

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(types.InlineKeyboardButton(text="Оплатить", url='https://testpay.parkpass.ru/#/?P=%s&C=%s' % (user_data['parking_id'], user_data['card_id'])))

    if result['data']['debt'] > 0:
        await message.answer(
            '<b>К оплате:</b> %s ₽\n'
            '<b>Время на парковке:</b> %s\n'
            '<b>Въезд:</b> %s\n'
            '<b>Номер карты:</b> %s\n'
            % (result['data']['debt'], duration, entered_at, user_data['card_id']),
            reply_markup=keyboard
        )
        await state.finish()
    else:
        await message.answer('Оплата не требуется')
        await state.finish()

async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    parking_list = Parking.objects.filter(approved=True).values('id', 'name')

    for parking in parking_list:
        if parking['name']:
            buttons.append(types.InlineKeyboardButton(text=parking['name'], callback_data="parking_%s" % parking['id']))

    keyboard.add(*buttons)

    await message.answer(
        "Привет, для оплаты парковочной карты, пожалуйста выберите свою парковку",
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
    dp.register_message_handler(parking_choosen, state=PaymentProcess.waiting_for_parking)
