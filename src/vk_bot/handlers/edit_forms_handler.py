from datetime import datetime

from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
    BaseStateGroup,
)
from src.common.logger import logger
from vkbottle.bot import Message, BotLabeler
import enum
from src.common.constants import (
    FORM_STATUSES_MAPPING,
    BotSettings,
    INTERVIEW_STATUSES_MAPPING,
)
from src.common.entities import ProjectTeamPATCH, ProjectTeamMemberPATCH
from src.vk_bot.bot import get_backend_sdk, state_dispenser
from src.common.utils import build_keyboard, validate_payload
from src.vk_bot.handlers.greeting_handler import KEYBOARD as GREETING_KEYBOARD
from dataclasses import asdict


edit_forms_labeler = BotLabeler()
edit_forms_labeler.vbml_ignore_case = True


EDIT_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Название команды"), color=KeyboardButtonColor.PRIMARY)
    .add(Text("Описание"), color=KeyboardButtonColor.PRIMARY)
    .add(Text("Участников"), color=KeyboardButtonColor.PRIMARY)
    .add(Text("Отменить заявку"), color=KeyboardButtonColor.NEGATIVE)
    .add(Text("Назад"), color=KeyboardButtonColor.PRIMARY)
    .get_json()
)


DELETION_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Да"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Отменить"), color=KeyboardButtonColor.PRIMARY)
    .get_json()
)


ACK_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Отправить"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Продолжить редактирование"), color=KeyboardButtonColor.PRIMARY)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)

FILLING_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


class EditFormStates(BaseStateGroup):
    FORM_SELECTION = enum.auto()
    EDIT_PART_SELECTION = enum.auto()
    EDIT_TEAM_NAME = enum.auto()
    EDIT_DESCRIPTION = enum.auto()
    EDIT_TEAM_MEMBERS = enum.auto()
    EDIT_ACK = enum.auto()


def _map_project_form(backend_data: dict) -> ProjectTeamPATCH:
    project = backend_data["project"]
    team_members = []
    for team_member in backend_data["members"]:
        team_member_dto = ProjectTeamMemberPATCH(
            id=team_member["id"],
            fullname=team_member["fullname"],
            role=team_member["role"],
            study_group=team_member["study_group"],
        )
        team_members.append(team_member_dto)
    return ProjectTeamPATCH(
        project_id=project["id"],
        project_name=project["name"],
        vk_sender_id=backend_data["vk_sender_id"],
        team_name=backend_data["team_name"],
        team_members=team_members,
        description=backend_data["description"] or "Без описания",
    )


async def _process_new_team(message: Message, payload: dict) -> None:
    backend_sdk = get_backend_sdk()
    attempt = payload.get("attempt", 1)
    if attempt >= BotSettings.find_team_retries:
        await message.answer(
            "Исчерпан лимит попыток, попробуйте позднее", keyboard=FILLING_KEYBOARD
        )
        return None
    project_team: ProjectTeamPATCH = payload["project_team"]
    search_name = message.text.strip()
    team = await backend_sdk.get_teams(search_name)
    if team:
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_TEAM_NAME,
            project_team=payload["project_team"],
            attempt=attempt + 1,
        )
        await message.answer(
            "Данная команда уже была на проектах Альфа Банка, пожалуйста, введите другое название",
            keyboard=FILLING_KEYBOARD,
        )
        return None
    project_team.team_name = search_name
    await state_dispenser.set(
        message.peer_id,
        EditFormStates.EDIT_ACK,
        project_team=project_team,
    )
    await message.answer(
        f"Ваша заявка:\n{str(project_team)}\n\nВы можете отправить обновлённую заявку, продолжить редактирование или отменить все изменения",
        keyboard=ACK_KEYBOARD,
    )


@edit_forms_labeler.private_message(text="Мои заявки")
async def get_form_status(message: Message):
    backend_sdk = get_backend_sdk()
    active_forms = await backend_sdk.get_peer_project_forms(message.peer_id)
    if not active_forms:
        await message.answer(
            "У вас пока нет отправленных заявок на студенческие проекты в этом семестре",
            keyboard=GREETING_KEYBOARD,
        )
        return
    forms_mapping = {}
    answer = "Ваши отправленные заявки:\n"
    for num, form in enumerate(active_forms, 1):
        interview = form.get("interview", {})
        formatted_interview = None
        if interview:
            status = interview.get("interview_status", "")
            status = INTERVIEW_STATUSES_MAPPING.get(status, "Ждёт обработки")
            date = interview.get("date")
            if date:
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)  # если ISO формат
                date = date.strftime("%d.%m %H:%M")
            else:
                date = "Не указана"
            url = interview.get("url") or "Не указана"
            formatted_interview = f"- Статус: {status}\n - Дата: {date}\n - URL: {url}"
        forms_mapping[num] = form
        answer += f"""{num}. Команда: {form["team_name"]}
Выбранный проект: {form["project"]["name"]}
Статус: {FORM_STATUSES_MAPPING.get(form["status"], "Ждёт обработки")}
Собеседование:\n {formatted_interview or "Не назначено"}\n
"""
    answer += "Вы можете изменить данные любой заявки, выбрав соответствующую"
    keyboard = (
        build_keyboard(
            [(f"№{num}", {"id": form["id"]}) for num, form in forms_mapping.items()],
            one_time=False,
            inline=True,
        )
        .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )
    await state_dispenser.set(
        message.peer_id,
        EditFormStates.FORM_SELECTION,
    )
    await message.answer(answer, keyboard=keyboard)


@edit_forms_labeler.private_message(state=EditFormStates.FORM_SELECTION)
async def handle_choosen_form(message: Message):
    try:
        choosen_form = message.get_payload_json()
        if not choosen_form:
            return
        backend_sdk = get_backend_sdk()
        form_detail = await backend_sdk.get_form_by_id(choosen_form["id"])  # type: ignore[index]
        project_form_dto = _map_project_form(form_detail[0])
        project_form_dto.form_id = choosen_form["id"]  # type: ignore[assignment, index]
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_PART_SELECTION,
            project_team=project_form_dto,
        )
        await message.answer(
            f"Выбранная заявка:\n{str(project_form_dto)}\n\nЧто именно Вы хотите изменить?",
            keyboard=EDIT_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling choosen form: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(
    state=EditFormStates.EDIT_PART_SELECTION, text="Название команды"
)
async def edit_team_name(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_TEAM_NAME,
            project_team=payload["project_team"],
        )
        await message.answer("Введите новое имя для команды", keyboard=FILLING_KEYBOARD)
    except Exception as e:
        logger.error(f"Error while editing team name: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(
    state=EditFormStates.EDIT_PART_SELECTION, text="Описание"
)
async def edit_description(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_DESCRIPTION,
            project_team=payload["project_team"],
        )
        await message.answer(
            "Введите новое описание, оно должно включать в себя технологический стек Вашей команды и прошлый опыт в учебных проектах УрФУ",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while editing team name: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(state=EditFormStates.EDIT_DESCRIPTION)
async def handle_new_description(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        description = message.text.strip()
        if len(description) < 15:
            await state_dispenser.set(
                message.peer_id,
                EditFormStates.EDIT_DESCRIPTION,
                project_team=project_team_dto,
            )
            await message.answer(
                """
Минимальная длина описания - 15 символов, пожалуйста дополните Ваш ответ.
""",
                keyboard=FILLING_KEYBOARD,
            )
            return
        project_team_dto.description = description
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_ACK,
            project_team=project_team_dto,
        )
        await message.answer(
            f"Ваша заявка:\n{str(project_team_dto)}\n\nВы можете отправить обновлённую заявку, продолжить редактирование или отменить все изменения",
            keyboard=ACK_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while editing team name: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(state=EditFormStates.EDIT_TEAM_NAME)
async def handle_team_name(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        await _process_new_team(message, payload)
    except Exception as e:
        logger.error(f"Error while editing team name: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(
    state=EditFormStates.EDIT_PART_SELECTION, text="Участников"
)
async def edit_team_members(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_TEAM_MEMBERS,
            project_team=project_team_dto,
        )
        await message.answer(
            BotSettings.edit_team_members_template,
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while editing team members: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(state=EditFormStates.EDIT_TEAM_MEMBERS)
async def handle_team_members(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        team_members = message.text
        team_members = [
            team_member.strip() for team_member in team_members.splitlines()
        ]
        if not team_members:
            logger.warning(f"Incorrect input data: {message.text}")
            await message.answer(
                "Пожалуйста введите корректные ФИО", keyboard=FILLING_KEYBOARD
            )
            return None
        if len(team_members) < 3:
            await message.answer(
                "Минимальное количество людей на данный проект - 3",
                keyboard=FILLING_KEYBOARD,  # TODO это лучше из бд получать
            )
            return None
        form_members = []
        for team_member in team_members:
            team_member = team_member.split(",")
            team_member_dto = ProjectTeamMemberPATCH(
                fullname=team_member[0].strip(),
                role=team_member[1].strip(),
                study_group=team_member[2].strip(),
            )
            form_members.append(team_member_dto)
        project_team_dto.team_members = form_members
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_ACK,
            project_team=project_team_dto,
        )
        await message.answer(
            f"Ваша заявка:\n{str(project_team_dto)}\n\nВы можете отправить обновлённую заявку, продолжить редактирование или отменить все изменения",
            keyboard=ACK_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while editing team members: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(
    state=EditFormStates.EDIT_PART_SELECTION, text=["Отменить заявку", "Да"]
)
async def delete_form(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        if message.text.strip().lower() == "да":
            if not project_team_dto.form_id:
                raise Exception("No form id in patch data")
            backend_sdk = get_backend_sdk()
            await backend_sdk.delete_form(project_team_dto.form_id)
            await message.answer(
                "Может, чем-то ещё могу Вам помочь?",
                keyboard=GREETING_KEYBOARD,
            )
            return
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_PART_SELECTION,
            project_team=project_team_dto,
        )
        await message.answer(
            f"{str(project_team_dto)}\n\nВы точно хотите отменить эту заявку? Если к заявке привязано собеседование, то оно также отменится.",
            keyboard=DELETION_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while deleting form: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(state=EditFormStates.EDIT_ACK, text="Отправить")
async def send_form(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        backend_sdk = get_backend_sdk()
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        if not project_team_dto.form_id:
            raise Exception("No form id in patch data")
        await backend_sdk.update_form(
            project_team_dto.form_id, asdict(project_team_dto)
        )
        await message.answer(
            "Форма успешно обновлена! Спасибо за уделенное время. Если что, просто пишите 'Начать' - и я уже тут!",
            keyboard=GREETING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while patching application form: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@edit_forms_labeler.private_message(
    state=EditFormStates.EDIT_ACK, text="Продолжить редактирование"
)
async def handle_edit_continuos(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        project_team_dto: ProjectTeamPATCH = payload["project_team"]
        await state_dispenser.set(
            message.peer_id,
            EditFormStates.EDIT_PART_SELECTION,
            project_team=project_team_dto,
        )
        await message.answer(
            f"Обновлённая форма:\n{str(project_team_dto)}\n\nЧто ещё хотите изменить?",
            keyboard=EDIT_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while patching application form: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")
