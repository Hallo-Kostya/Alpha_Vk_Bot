from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
    BaseStateGroup,
)
import enum
from vkbottle.bot import Message, BotLabeler
from src.common.utils import build_keyboard, format_team, validate_payload
from src.vk_bot.bot import state_dispenser, get_backend_sdk
from src.common.entities import ProjectTeam, ProjectTeamMember
from src.common.logger import logger
from src.vk_bot.handlers.greeting_handler import KEYBOARD as GREETING_KEYBOARD
from src.common.constants import BotSettings


form_labeler = BotLabeler()
form_labeler.vbml_ignore_case = True


class FormStates(BaseStateGroup):
    WAITING_FOR_PROJECT = enum.auto()
    WAITING_FOR_TEAM_QUESTION = enum.auto()
    WAITING_FOR_TEAM_NAME = enum.auto()
    WAITING_FOR_TEAM_MEMBERS = enum.auto()
    WAITING_FOR_DESCRIPTION = enum.auto()
    WAITING_FOR_ACK = enum.auto()


FILLING_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


TEAM_FIND_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Создать новую"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


FINAL_KEYBOARD = (
    Keyboard(inline=True)
    .add(Text("Отправить форму"), color=KeyboardButtonColor.POSITIVE)
    .add(Text("Заполнить заново"), color=KeyboardButtonColor.SECONDARY)
    .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
    .get_json()
)


async def _process_new_team(message: Message, payload: dict) -> None:
    backend_sdk = get_backend_sdk()
    attempt = payload.get("attempt", 1)
    if attempt >= BotSettings.find_team_retries:
        await message.answer(
            "Исчерпан лимит попыток, попробуйте позднее", keyboard=FILLING_KEYBOARD
        )
        return None
    project_team: ProjectTeam = payload["project_team"]
    search_name = project_team.team_name if attempt == 1 else message.text.strip()
    team = await backend_sdk.get_teams(search_name)
    if team:
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_NAME,
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
        FormStates.WAITING_FOR_TEAM_MEMBERS,
        project_team=project_team,
    )
    await message.answer(
        "Тогда давайте начнем знакомство!\n" + BotSettings.edit_team_members_template,
        keyboard=FILLING_KEYBOARD,
    )


@form_labeler.private_message(text=["Создать заявку", "Заполнить заново"])
async def fill_form(message: Message):
    try:
        if message.text.strip() == "Заполнить заново":
            message.state_peer.payload.pop("project_team", "")  # type: ignore[uniot-attr]
        backend_sdk = get_backend_sdk()
        available_projects = await backend_sdk.get_available_projects_for_user(
            message.peer_id
        )
        if not available_projects:
            await message.answer(
                "К сожалению на данный момент нет доступных для записи проектов"
            )
            return None
        keyboard = (
            build_keyboard(
                [
                    (project["name"], {"id": project["id"], "name": project["name"]})
                    for project in available_projects
                ],
                one_time=False,
                inline=True,
            )
            .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
            .get_json()
        )
        await state_dispenser.set(message.peer_id, FormStates.WAITING_FOR_PROJECT)
        projects_formatted = "\n - ".join(
            project["name"] for project in available_projects
        )
        await message.answer(
            f"Доступные для записи проекты:\n - {projects_formatted}\nНа какой из них Вы хотите оставить заявку?",
            keyboard=keyboard,
        )
    except Exception as e:
        logger.error(f"Error while handling fill form: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_PROJECT)
async def handle_choosen_project(message: Message):
    try:
        project_data = message.get_payload_json()
        if not project_data:
            return
        project_team_dto = ProjectTeam(
            project_id=project_data["id"],  # type: ignore
            project_name=project_data["name"],  # type: ignore
            vk_sender_id=message.peer_id,
        )
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_QUESTION,
            project_team=project_team_dto,
        )
        await message.answer(
            "Отлично! Напишите, пожалуйста, название Вашей команды",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling choosen project: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_QUESTION)
async def handle_team_question(message: Message):
    if not (payload := await validate_payload(message)):
        return
    try:
        if message.text.lower().strip() == "создать новую":
            await message.answer(
                "Секунду, проверяем валидность названия...",
            )
            payload.pop("attempt")
            await _process_new_team(message, payload)
            return
        attempt = payload.get("attempt", 1)
        if attempt >= BotSettings.find_team_retries:
            project_team: ProjectTeam = payload["project_team"]
            project_team.team_name = message.text.strip()
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_TEAM_QUESTION,
                project_team=project_team,
                attempt=attempt + 1,
            )
            logger.error(
                f"User with id {message.peer_id} reached find team retries limit"
            )
            await message.answer(
                "Лимит попыток. Давайте лучше создадим новую команду?",
                keyboard=TEAM_FIND_KEYBOARD,
            )
            return None
        backend_sdk = get_backend_sdk()
        team = await backend_sdk.get_teams(message.text.strip())
        if not team:
            project_team: ProjectTeam = payload["project_team"]
            project_team.team_name = message.text.strip()
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_TEAM_QUESTION,
                project_team=project_team,
                attempt=attempt + 1,
            )
            await message.answer(
                "Данная команда не найдена в нашей базе. Можете ввести новое название или создать новую",
                keyboard=TEAM_FIND_KEYBOARD,
            )
            return None
        team = team[0]
        project_team_dto: ProjectTeam = payload["project_team"]
        project_team_dto.team_name = message.text.strip()
        team_members = []
        for member in team["members"]:
            student = member["student"]
            team_members.append(
                ProjectTeamMember(
                    fullname=f"{student['last_name']} {student['first_name']} {student['patronymic'] or ''}",
                    role=member["role"],
                    study_group=member["study_group"],
                )
            )
        project_team_dto.team_members = team_members

        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_MEMBERS,
            project_team=project_team_dto,
        )
        team_info_repr = format_team(team)
        await message.answer(
            f"Нашлась такая команда!\n\n{team_info_repr}\n\nЖелаете изменить данные?",
            keyboard=Keyboard(one_time=True, inline=False)
            .add(Text("Да"), color=KeyboardButtonColor.PRIMARY)
            .add(Text("Нет"), color=KeyboardButtonColor.SECONDARY)
            .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
            .get_json(),
        )
    except Exception as e:
        logger.error(f"Error while handling team question: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_NAME)
async def handle_new_team(message: Message):
    if not (payload := await validate_payload(message)):
        return
    try:
        await _process_new_team(message, payload)
    except Exception as e:
        logger.error(f"Error while handling new team: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_MEMBERS)
async def handle_team_members(message: Message):
    try:
        if not (payload := await validate_payload(message)):
            return
        if message.text.lower().strip() == "нет":
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_ACK,
                project_team=payload["project_team"],
            )
            await message.answer(
                f"""
Заявка составлена! Пожалуйста, проверьте правильность отправляемых данных:\n{str(payload["project_team"])}
""",
                keyboard=FINAL_KEYBOARD,
            )
            return None
        if message.text.lower().strip() == "да":
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_TEAM_MEMBERS,
                project_team=payload["project_team"],
            )
            await message.answer(
                BotSettings.edit_team_members_template,
                keyboard=FILLING_KEYBOARD,
            )
            return None
        project_team_dto: ProjectTeam = payload["project_team"]
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
            try:
                team_member = team_member.split(",")
                team_member_dto = ProjectTeamMember(
                    fullname=team_member[0].strip(),
                    role=team_member[1].strip(),
                    study_group=team_member[2].strip(),
                )
                form_members.append(team_member_dto)
            except ValueError:
                await state_dispenser.set(
                    message.peer_id,
                    FormStates.WAITING_FOR_TEAM_MEMBERS,
                    project_team=payload["project_team"],
                )
                await message.answer(
                    "Некорретные данные, пожалуйста проверьте и отправьте информацию об участниках заново",
                    keyboard=FILLING_KEYBOARD,
                )
                return None
        project_team_dto.team_members = form_members
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_DESCRIPTION,
            project_team=project_team_dto,
        )
        await message.answer(
            """
Отлично! Теперь, пожалуйста, опишите технологический стек Вашей команды и прошлый опыт в учебных проектах УрФУ (краткое описание и итоговый балл БРС)
""",
            keyboard=FILLING_KEYBOARD,
        )
    except IndexError:
        await message.answer(
            "Пожалуйста, введите корректные данные, данные участников должны быть с новой строки",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling team members: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_DESCRIPTION)
async def fill_description(message: Message):
    if not (payload := await validate_payload(message)):
        return
    try:
        description = message.text.strip()
        project_team_dto: ProjectTeam = payload["project_team"]
        if len(description) < 15:
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_DESCRIPTION,
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
            FormStates.WAITING_FOR_ACK,
            project_team=project_team_dto,
        )
        await message.answer(
            f"""
Заявка составлена! Пожалуйста, проверьте правильность отправляемых данных:\n{str(project_team_dto)}
""",
            keyboard=FINAL_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while sending application POST: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_ACK, text="Отправить форму")
async def send_form(message: Message):
    if not (payload := await validate_payload(message)):
        return
    backend_sdk = get_backend_sdk()
    try:
        project_team_dto: ProjectTeam = payload["project_team"]
        await backend_sdk.create_project_application(project_team_dto)
        await message.answer(
            "Форма успешно отправлена! Спасибо за уделенное время",
            keyboard=GREETING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while sending application POST: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")
