from vkbottle.bot import Bot, BotLabeler
from vkbottle import BuiltinStateDispenser
from src.constants import VK_GROUP_TOKEN

state_dispenser = BuiltinStateDispenser()

chat_labeler = BotLabeler()

bot = Bot(
    VK_GROUP_TOKEN,
    labeler=chat_labeler,
    state_dispenser=state_dispenser
)
