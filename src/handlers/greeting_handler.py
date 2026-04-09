from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
)
from vkbottle.bot import Message, BotLabeler
from src.constants import BotSettings


greeting_labeler = BotLabeler()
greeting_labeler.vbml_ignore_case = True


KEYBOARD = (
    Keyboard(inline=True)
    .add(Text("Оставить заявку на проект"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Узнать статус заявки"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("Напомнить время собеседования"), color=KeyboardButtonColor.SECONDARY)
    .get_json()
)


@greeting_labeler.private_message(text=["Привет", "Здравствуйте", "Начать", "Отменить"])
async def greet(message: Message):
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)


@greeting_labeler.private_message(text="Узнать статус заявки")
async def get_form_status(message: Message):  # TODO
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)


@greeting_labeler.private_message(text="Напомнить время собеседования")
async def get_interview_info(message: Message):  # TODO
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)
