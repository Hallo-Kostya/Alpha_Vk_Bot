from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
    BaseStateGroup,
)
import enum
from vkbottle.bot import Message, BotLabeler
from src.utils import build_keyboard
from src.bot import state_dispenser
from dataclasses import dataclass, field
from src.logger import logger
from src.handlers.greeting_handler import KEYBOARD as GREETING_KEYBOARD


@dataclass(slots=True)
class ProjectTeamMember:
    first_name: str
    last_name: str
    patronymic: str | None = None
    unit_id: int | None = None  # заполняется после создания модели в бд

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic or ''}"


@dataclass(slots=True)
class ProjectTeam:
    project_id: int
    project_name: str
    team_name: str | None = None
    team_members: list[ProjectTeamMember] = field(default_factory=list)
    status: str = "PENDING"

    def __str__(self):
        return f"""Команда: {self.team_name}
Выбранный проект: {self.project_name}
Данные участников команды:
{"\n".join(str(t_m) for t_m in self.team_members)}"""


form_labeler = BotLabeler()
form_labeler.vbml_ignore_case = True


class FormStates(BaseStateGroup):
    WAITING_FOR_PROJECT = enum.auto()
    WAITING_FOR_TEAM_NAME = enum.auto()
    WAITING_FOR_TEAM_MEMBERS = enum.auto()
    WAITING_FOR_ACK = enum.auto()
    WAITING_FOR_SAVE = enum.auto()


FILLING_KEYBOARD = (
    Keyboard(one_time=True, inline=False)
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

MOCK_PROJECTS = [
    {"id": 1, "name": "CRM система для управления проектами"},
    {"id": 2, "name": "Проект по обходу 115 ФЗ"},
]


@form_labeler.private_message(text=["Оставить заявку на проект", "Заполнить заново"])
async def fill_form(message: Message):
    # TODO active_projects = await backend_sdk.get_active_projects()
    active_projects = [(project["name"], project) for project in MOCK_PROJECTS]
    if not active_projects:
        await message.answer(
            "К сожалению на данный момент нет доступных для записи проектов"
        )
        return None
    keyboard = (
        build_keyboard(active_projects, one_time=False, inline=True)
        .add(Text("Отменить"), color=KeyboardButtonColor.NEGATIVE)
        .get_json()
    )
    await state_dispenser.set(message.peer_id, FormStates.WAITING_FOR_PROJECT)
    await message.answer(
        "На какой из проектов Вы хотите записаться?", keyboard=keyboard
    )


@form_labeler.private_message(state=FormStates.WAITING_FOR_PROJECT)
async def handle_choosen_project(message: Message):
    try:
        project_data = message.get_payload_json()
        project_team_dto = ProjectTeam(
            project_id=project_data["id"],  # type: ignore
            project_name=project_data["name"],  # type: ignore
        )
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_NAME,
            project_team=project_team_dto,
        )
        await message.answer(
            "Отлично! Напишите, пожалуйста, название Вашей команды",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling choosen project: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_NAME)
async def handle_team_name(message: Message):
    try:
        if not message.state_peer or "project_team" not in message.state_peer.payload:
            logger.error(
                f"Error while handling team name: incorrect payload: {message.state_peer}"
            )
            await message.answer(
                "Возникли проблемы с выбором проекта, повторите попытку, пожалуйста"
            )
            return None
        project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
        project_team_dto.team_name = message.text
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_MEMBERS,
            project_team=project_team_dto,
        )
        await message.answer(
            """Прекрасное название!
А теперь, пожалуйста, напишите Фамилию, Имя, Отчество (при наличии) всех участников Вашей команды через запятую:
Иванов Иван Иванович, Дмитриев Дмитрий, ...
""",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling team name: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_MEMBERS)
async def handle_team_members(message: Message):
    try:
        if not message.state_peer or "project_team" not in message.state_peer.payload:
            logger.error(
                f"Error while handling team members: incorrect payload: {message.state_peer}"
            )
            await message.answer(
                "Возникли проблемы с выбором проекта, повторите попытку, пожалуйста"
            )
            return None
        project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
        team_members = message.text
        team_members = [team_member.strip() for team_member in team_members.split(",")]
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
        for team_member in team_members:
            team_member = team_member.split(" ")
            team_member_dto = ProjectTeamMember(
                first_name=team_member[1],
                last_name=team_member[0],
                patronymic=team_member[2] if len(team_member) > 2 else None,
            )
            project_team_dto.team_members.append(team_member_dto)
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
    except IndexError:
        await message.answer(
            "Пожалуйста, введите корректные данные, ФИО участников должны быть через запятую",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling team members: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(text="Отправить форму")
async def send_form(message: Message):
    # TODO backend_sdk.send_form
    await message.answer(
        "Форма успешно отправлена! Спасибо за уделенное время",
        keyboard=GREETING_KEYBOARD,
    )
