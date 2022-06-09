import asyncio

from aiogram_broadcaster import TextBroadcaster

VALET_BOT_TOKEN = '5400138957:AAFFkszKGg4aBK_S_TTFyqaE7lBZDJTHG8M'


def send_message_by_valet_bot(message):
    async def run():
        # Initialize a text broadcaster (you can directly pass a token)
        broadcaster = TextBroadcaster([688045242, '-643455758'], message, bot_token=VALET_BOT_TOKEN)

        # Run the broadcaster and close it afterwards
        try:
            await broadcaster.run()
        finally:
            await broadcaster.close_bot()

    asyncio.run(run())

