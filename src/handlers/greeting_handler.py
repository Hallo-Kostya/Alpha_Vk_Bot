from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
)
from vkbottle.bot import Message, BotLabeler
from src.constants import BotSettings, FORM_STATUSES_MAPPING
from src.bot import get_backend_sdk

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
async def get_form_status(message: Message):
    backend_sdk = get_backend_sdk()
    active_forms = await backend_sdk.get_peer_project_forms(message.peer_id)
    if not active_forms:
        await message.answer("У вас нет отправленных заявок на студенческие проекты в этом семестре", keyboard=KEYBOARD)
        return
    answer = "Ваши отправленные заявки:\n"
    for num, form in enumerate(active_forms, 1):
        answer += f"""{num}. Команда: {form["team"]["name"]}
Выбранный проект: {form["project"]["name"]}
Статус: {FORM_STATUSES_MAPPING.get(form["status"], "Ждёт обработки")}
Собеседование: {form["meeting"] or "Не назначено"}\n
"""
    await message.answer(answer, keyboard=KEYBOARD)


@greeting_labeler.private_message(text="Напомнить время собеседования")
async def get_interview_info(message: Message):
    await message.answer(BotSettings.base_greeting, keyboard=KEYBOARD)
