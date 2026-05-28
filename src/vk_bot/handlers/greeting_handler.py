from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
)
from vkbottle.bot import Message, BotLabeler
from src.common.constants import BotSettings

greeting_labeler = BotLabeler()
greeting_labeler.vbml_ignore_case = True


KEYBOARD = (
    Keyboard(inline=True)
    .add(Text("Создать заявку"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    # .add(Text("Проекты"), color=KeyboardButtonColor.SECONDARY)
    .get_json()
)


@greeting_labeler.private_message(text=["Привет", "Здравствуйте", "Начать", "Отменить"])
async def greet(message: Message):
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)


@greeting_labeler.private_message(text="Проекты")
async def get_interview_info(message: Message):
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)
