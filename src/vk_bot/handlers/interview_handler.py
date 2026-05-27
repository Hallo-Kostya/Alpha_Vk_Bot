from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Message, BotLabeler
import enum
from src.vk_bot.bot import state_dispenser, get_backend_sdk
from src.common.logger import logger
import re
from datetime import UTC, datetime


DATE_PATTERN = re.compile(r"(?P<date>\d{2}\.\d{2})\s*,?\s*(?P<time>\d{2}:\d{2})")

FILLING_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

ACK_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Да"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Нет"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


interview_labeler = BotLabeler()
interview_labeler.vbml_ignore_case = True


class InterviewStates(BaseStateGroup):
    DATE_CHOOSE = enum.auto()
    DATE_VERIFY = enum.auto()


@interview_labeler.private_message(state=InterviewStates.DATE_CHOOSE)
async def choose_interview_date(message: Message):
    if not (payload := await validate_payload(message)):
        return
    possible_dates: dict[str, list[str]] = payload["possible_dates"]
    choosen_date = message.text.strip()

    match = DATE_PATTERN.search(choosen_date)
    if match:
        date = match.group("date")
        time = match.group("time")
        if (date not in possible_dates) or (time not in possible_dates[date]):
            await state_dispenser.set(
                message.peer_id,
                InterviewStates.DATE_CHOOSE,
                possible_dates=possible_dates,
                application_id=payload["application_id"],
            )
            await message.answer(
                "Пожалуйста, перепроверьте указанную дату, мы не можем назначить на неё интервью",
                keyboard=FILLING_KEYBOARD,
            )
            return
        current_year = datetime.now(UTC).year

        dt = datetime.strptime(f"{date}.{current_year} {time}", "%d.%m.%Y %H:%M")
        await state_dispenser.set(
            message.peer_id,
            InterviewStates.DATE_VERIFY,
            possible_dates=possible_dates,
            choosen_date=dt,
            application_id=payload["application_id"],
        )
        await message.answer(
            f"Отлично! Давайте на всякий случай проверим ещё раз. Выбранная дата для собеседования: {date}, {time}. Бронируем слот?",
            keyboard=ACK_KEYBOARD,
        )
    else:
        await state_dispenser.set(
            message.peer_id,
            InterviewStates.DATE_CHOOSE,
            possible_dates=possible_dates,
            application_id=payload["application_id"],
        )
        await message.answer(
            "Пожалуйста, проверьте формат. Переданная дата должна быть в формате: '28.05, 17:00'.",
            keyboard=FILLING_KEYBOARD,
        )
        return


@interview_labeler.private_message(state=InterviewStates.DATE_VERIFY)
async def ack_choosen_date(message: Message):
    if not (payload := await validate_payload(message)):
        return
    response = message.text.lower().strip()
    if response == "да":
        backend_sdk = get_backend_sdk()
        await backend_sdk.post_interview(
            payload["application_id"], payload["choosen_date"]
        )
        await message.answer(
            "Успешно создали интервью! Ссылка на встречу придет Вам в этот же чат, спасибо за уделённое время."
        )
        return
    else:
        await state_dispenser.set(
            message.peer_id,
            InterviewStates.DATE_CHOOSE,
            possible_dates=payload["possible_dates"],
            application_id=payload["application_id"],
        )
        await message.answer(
            f"Хорошо, выберите, пожалуйста, новый слот из доступных:\n\n{format_dates(payload['possible_dates'])}",
            keyboard=FILLING_KEYBOARD,
        )
        return


async def validate_payload(message: Message) -> dict | None:
    if (
        not message.state_peer
        or "possible_dates" not in message.state_peer.payload
        or "application_id" not in message.state_peer.payload
    ):
        logger.error(
            f"Error while handling team name: incorrect payload: {message.state_peer}"
        )
        await message.answer(
            "Возникли проблемы с выбором времени для интервью, повторите попытку позднее, пожалуйста"
        )
        return None
    return message.state_peer.payload


def format_dates(possible_dates: dict[str, list[str]]) -> str:
    formatted_dates = "Доступные слоты:\n\n"
    for date in possible_dates:
        formatted_dates += f"{date}:\n"
        for hour in possible_dates[date]:
            formatted_dates += f" - {hour};\n"
    formatted_dates += "Пример ответа: '28.05, 16:00'"
    return formatted_dates
