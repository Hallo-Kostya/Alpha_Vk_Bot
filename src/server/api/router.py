from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from src.server.api.schemas import (
    NotifyDeclineAccept,
    InterviewPossibleDates,
    InterviewUpdate,
)
from src.vk_bot.bot import bot
from src.server.auth import AuthService
from random import randint
from src.vk_bot.bot import state_dispenser
from src.vk_bot.handlers.interview_handler import InterviewStates


router = APIRouter(prefix="/v1", dependencies=[Depends(AuthService.verify_service)])


@router.get("/")
async def base():
    return "Hello world"


@router.post("/{vk_sender_id}/notify_decline/")
async def notify_decline(vk_sender_id: int, data: NotifyDeclineAccept) -> dict:
    message = f"""Здравствуйте!
К сожалению, мы приняли решение отклонить Вашу заявку от команды: {data.team_name} на проект: {data.project_name}"""
    await bot.api.messages.send(
        user_id=vk_sender_id, message=message, random_id=randint(1, 2**31)
    )
    return {
        "success": f"User with id: {vk_sender_id} was successfully notified that his application has been declined"
    }


@router.post("/{vk_sender_id}/notify_accept/")
async def notify_accept(vk_sender_id: int, data: NotifyDeclineAccept) -> dict:
    message = f"""Здравствуйте!
Ваша заявка от команды: {data.team_name} на проект: {data.project_name} одобрена!
Дальнейшие указания ожидайте здесь же."""
    await bot.api.messages.send(
        user_id=vk_sender_id, message=message, random_id=randint(1, 2**31)
    )
    return {
        "success": f"User with id: {vk_sender_id} was successfully notified that his application has been accepted"
    }


@router.post("/{vk_sender_id}/notify_interview/choose_date/")
async def notify_interview_choose_date(
    vk_sender_id: int, data: InterviewPossibleDates
) -> dict:
    possible_dates = _preprocess_dates(data.possible_dates)
    formatted_dates = "Доступные слоты:\n\n"
    for date in possible_dates:
        formatted_dates += f"{date}:\n"
        for hour in possible_dates[date]:
            formatted_dates += f" - {hour};\n"
    formatted_dates += "\nПример ответа: '28.05, 16:00'"
    await state_dispenser.set(
        vk_sender_id,
        InterviewStates.DATE_CHOOSE,
        possible_dates=possible_dates,
        application_id=data.application_id,
    )
    message = f"""Здравствуйте!
Ваша заявка от команды: {data.team_name} на проект: {data.project_name} была одобрена для проведения интервью!
Пожалуйста, выберите удобную для Вас дату и время для проведения собеседования.

{formatted_dates}
"""
    await bot.api.messages.send(
        user_id=vk_sender_id, message=message, random_id=randint(1, 2**31)
    )
    return {
        "success": f"User with id: {vk_sender_id} was successfully notified that his application status has been changed to 'INTERVIEW'"
    }


@router.post("/{vk_sender_id}/notify_interview/update/")
async def notify_interview_updated(vk_sender_id: int, data: InterviewUpdate) -> dict:
    url = data.url
    date = data.date

    message = "Здравствуйте! Обновлёна информация по Вашему интервью.\n"
    if url:
        message += f"Добавлена ссылка на подключение к звонку: {url}\n"
    if date:
        message += (
            f"Изменена дата собеседования, новая дата: {date.strftime('%d.%m %H:%M')}"
        )
    await bot.api.messages.send(
        user_id=vk_sender_id, message=message, random_id=randint(1, 2**31)
    )
    return {
        "success": f"User with id: {vk_sender_id} was successfully notified that his interview info was updated"
    }


def _preprocess_dates(possible_dates: list[datetime]) -> dict:
    result = defaultdict(list)

    for dt in possible_dates:
        day_key = dt.strftime("%d.%m")
        time_value = dt.strftime("%H:%M")

        result[day_key].append(time_value)

    return dict(result)
