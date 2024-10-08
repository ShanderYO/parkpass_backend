import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions, executor

from base.utils import get_logger

API_TOKEN = '5534371311:AAH8GmzjCTz5tbdKjcDA-jNO_bJIhn-ZblY'

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('broadcast')

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)


async def send_message(user_id: int, text: str, photos: list = []) -> bool:
    """
    Safe messages sender

    :param user_id:
    :param text:
    :param disable_notification:
    :return:
    """
    import telegram
    from telegram import InputMediaPhoto

    try:
        if len(photos) > 0:
            try:
                if len(photos) > 1:
                    media = types.MediaGroup()

                    i = 0
                    for photo in photos:
                        media.attach_photo(photo, caption=text if i == 0 else '', parse_mode=types.ParseMode.HTML)
                        i += 1

                    await bot.send_media_group(user_id, media=media)
                else:
                    await bot.send_photo(user_id, photo=photos[0], caption=text)

            except Exception as e:
                get_logger().info(e)
                print(e)
                await bot.send_message(user_id, text, parse_mode=types.ParseMode.HTML)

        else:
            await bot.send_message(user_id, text, parse_mode=types.ParseMode.HTML)
        await bot.close()
    except exceptions.BotBlocked:
        log.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        log.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        log.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        log.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        log.exception(f"Target [ID:{user_id}]: failed")
    else:
        log.info(f"Target [ID:{user_id}]: success")
        return True
    return False


async def broadcaster(user_ids, message, photos) -> int:
    """
    Simple broadcaster

    :return: Count of messages
    """
    count = 0
    try:
        for user_id in user_ids:
            if await send_message(user_id, message, photos):
                count += 1
            await asyncio.sleep(.05)  # 20 messages per second (Limit: 30 messages per second)
    finally:
        log.info(f"{count} messages successful sent.")

    return count


def send_message_by_valet_bot(message, chats, photos):
    return broadcaster(chats, message, photos)

