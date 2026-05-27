from vkbottle.bot import Bot, BotLabeler
from vkbottle import BuiltinStateDispenser
from src.common.constants import VK_GROUP_TOKEN
import aiohttp
from src.vk_bot.http_client import HttpClient
from src.vk_bot.backend_sdk import BackendSdk

backend_sdk: BackendSdk

session: aiohttp.ClientSession

state_dispenser = BuiltinStateDispenser()

chat_labeler = BotLabeler()

bot = Bot(VK_GROUP_TOKEN, labeler=chat_labeler, state_dispenser=state_dispenser)


async def on_startup():
    global backend_sdk, session
    session = aiohttp.ClientSession()
    http_client = HttpClient(session)
    backend_sdk = BackendSdk(http_client)


async def on_shutdown():
    global session
    await session.close()


def get_backend_sdk():
    global backend_sdk
    return backend_sdk
