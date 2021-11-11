import django
import os

import sys
sys.path.append("/app")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parkpass_backend.settings")
django.setup()

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
from TelegramPaymentBot.handlers.common import register_handlers_common

logger = logging.getLogger(__name__)

BOT_TOKEN = "2058518674:AAGz3qQD0wGPO0N2gKF0JanVgrMXwmNbjD8"

# Регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Выбрать парковку"),
        # BotCommand(command="/cancel", description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


async def main():
    # Настройка логирования в stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.error("Starting bot")

    # Парсинг файла конфигурации

    # Объявление и инициализация объектов бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация хэндлеров
    register_handlers_common(dp)

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    # await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())