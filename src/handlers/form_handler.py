from vkbottle import (
    Text,
    Keyboard,
    KeyboardButtonColor,
    BaseStateGroup,
)
import enum
from vkbottle.bot import Message, BotLabeler
from src.utils import build_keyboard, format_team
from src.bot import state_dispenser, get_backend_sdk
from src.entities import ProjectTeam, ProjectTeamMember
from src.logger import logger
from src.handlers.greeting_handler import KEYBOARD as GREETING_KEYBOARD


form_labeler = BotLabeler()
form_labeler.vbml_ignore_case = True


class FormStates(BaseStateGroup):
    WAITING_FOR_PROJECT = enum.auto()
    WAITING_FOR_TEAM_QUESTION = enum.auto()
    WAITING_FOR_TEAM_NAME = enum.auto()
    WAITING_FOR_TEAM_MEMBERS = enum.auto()
    WAITING_FOR_ACK = enum.auto()
    WAITING_FOR_SAVE = enum.auto()


FIND_TEAM_RETRIES = 5

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


@form_labeler.private_message(text=["Оставить заявку на проект", "Заполнить заново"])
async def fill_form(message: Message):
    backend_sdk = get_backend_sdk()
    available_projects = await backend_sdk.get_available_projects_for_user(message.peer_id)
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
    projects_formatted = "\n - ".join(project["name"] for project in available_projects)
    await message.answer(
        f"Доступные для записи проекты:\n - {projects_formatted}\nНа какой из них Вы хотите записаться?", keyboard=keyboard
    )


@form_labeler.private_message(state=FormStates.WAITING_FOR_PROJECT)
async def handle_choosen_project(message: Message):
    try:
        project_data = message.get_payload_json()
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
    if not message.state_peer or "project_team" not in message.state_peer.payload:
        logger.error(
            f"Error while handling team name: incorrect payload: {message.state_peer}"
        )
        await message.answer(
            "Возникли проблемы с выбором проекта, повторите попытку позднее, пожалуйста"
        )
        return None
    if message.text.lower().strip() == "создать новую":
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_NAME,
            project_team=message.state_peer.payload["project_team"],
        )
        await message.answer(
            "Хорошо, пожалуйста, напишите финальное название Вашей будущей команды",
            keyboard=FILLING_KEYBOARD,
        )
        return None
    attempt = message.state_peer.payload.get("attempt", 1)
    if attempt >= FIND_TEAM_RETRIES:
        logger.error(f"User with id {message.peer_id} reached find team retries limit")
        await message.answer(
            "Лимит попыток. Давайте лучше создадим новую команду?",
            keyboard=TEAM_FIND_KEYBOARD,
        )
        return None
    backend_sdk = get_backend_sdk()
    team = await backend_sdk.get_teams(message.text.strip())
    if not team:
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_QUESTION,
            project_team=message.state_peer.payload["project_team"],
            attempt = attempt + 1
        )
        await message.answer(
            "Данная команда не найдена в нашей базе. Можете ввести новое название или создать новую",
            keyboard=TEAM_FIND_KEYBOARD,
        )
        return None
    team = team[0]
    project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
    project_team_dto.team_name = message.text.strip()
    project_team_dto.team_id = team["id"]
    members = []
    for member in team["members"]:
        student = member["student"]
        members.append(ProjectTeamMember(
            fullname=f"{student["last_name"]} {student["first_name"]} {student["patronymic"] or ""}",
            project_role=member["role"],
            academic_group=member["study_group"],
        ))
    project_team_dto.form_members=members

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


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_NAME)
async def hanlde_new_team(message: Message):
    if not message.state_peer or "project_team" not in message.state_peer.payload:
        logger.error(
            f"Error while handling team name: incorrect payload: {message.state_peer}"
        )
        await message.answer(
            "Возникли проблемы с выбором проекта, повторите попытку позднее, пожалуйста"
        )
        return None
    backend_sdk = get_backend_sdk()
    team_name = message.text.strip()
    team = await backend_sdk.get_teams(team_name)
    attempt = message.state_peer.payload.get("attempt", 1)
    if attempt >= FIND_TEAM_RETRIES:
        await message.answer("Исчерпан лимит попыток, попробуйте позднее", keyboard=FILLING_KEYBOARD)
        return None
    if team:
        await state_dispenser.set(
            message.peer_id,
            FormStates.WAITING_FOR_TEAM_NAME,
            project_team=message.state_peer.payload["project_team"],
            attempt=attempt + 1,
        )
        await message.answer("Данная команда уже была на проектах Альфа Банка, пожалуйста, введите другое название", keyboard=FILLING_KEYBOARD)
        return None
    project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
    project_team_dto.team_name = team_name
    await state_dispenser.set(
        message.peer_id,
        FormStates.WAITING_FOR_TEAM_MEMBERS,
        project_team=project_team_dto,
    )
    await message.answer(
            """Тогда давайте начнем знакомство!
Пожалуйста, напишите Фамилию, Имя, Отчество (при наличии) всех участников Вашей команды, а также их роли и академические группы через запятую.
Общий формат должен получиться такой:

Иванов Иван Иванович, дизайнер, РИ-111111
Дмитриев Дмитрий, бекендер, РИ-123456
Бурдук Константин Евгеньевич, фронтендер, РИ-123456
Воронцов Тимофей Григорьевич, аналитик, РИ-123020
Криштиано Роналдо, тимлид, РИ-330943""",
            keyboard=FILLING_KEYBOARD,
    )


@form_labeler.private_message(state=FormStates.WAITING_FOR_TEAM_MEMBERS)
async def handle_team_members(message: Message):
    try:
        if not message.state_peer or not message.state_peer.payload:
            logger.error(
                f"Error while handling team members: incorrect payload: {message.state_peer}"
            )
            await message.answer(
                "Возникли проблемы с обработкой Вашего ответа, повторите попытку позднее, пожалуйста"
            )
            return None
        if message.text.lower().strip() == "нет":
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_ACK,
                project_team=message.state_peer.payload["project_team"],
            )
            await message.answer(
            f"""
Заявка составлена! Пожалуйста, проверьте правильность отправляемых данных:\n{str(message.state_peer.payload["project_team"])}
""",
            keyboard=FINAL_KEYBOARD,
        )
            return None
        if message.text.lower().strip() == "да":
            await state_dispenser.set(
                message.peer_id,
                FormStates.WAITING_FOR_TEAM_MEMBERS,
                project_team=message.state_peer.payload["project_team"],
            )
            await message.answer(
                """Пожалуйста, напишите итоговый состав вашей команды: Фамилию, Имя, Отчество (при наличии) всех участников, а также их роли и академические группы через запятую.
Общий формат должен получиться такой:

Иванов Иван Иванович, дизайнер, РИ-111111
Дмитриев Дмитрий, бекендер, РИ-123456
Бурдук Константин Евгеньевич, фронтендер, РИ-123456
Воронцов Тимофей Григорьевич, аналитик, РИ-123020
Криштиано Роналдо, тимлид, РИ-330943""",
            keyboard=FILLING_KEYBOARD,
            )
            return None
        project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
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
        for team_member in team_members:
            team_member = team_member.split(",")
            team_member_dto = ProjectTeamMember(
                fullname=team_member[0],
                project_role=team_member[1],
                academic_group=team_member[2],  #TODO проверка на какашки
            )
            project_team_dto.form_members.append(team_member_dto)
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
            "Пожалуйста, введите корректные данные, ФИО участников должны быть с новой строки",
            keyboard=FILLING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while handling team members: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")


@form_labeler.private_message(state=FormStates.WAITING_FOR_ACK, text="Отправить форму")
async def send_form(message: Message):
    if not message.state_peer or not message.state_peer.payload:
        logger.error(
            f"Error while handling team members: incorrect payload: {message.state_peer}"
        )
        await message.answer(
            "Возникли проблемы с обработкой Вашего ответа, повторите попытку позднее, пожалуйста"
        )
        return None
    backend_sdk = get_backend_sdk()
    try:
        project_team_dto: ProjectTeam = message.state_peer.payload["project_team"]
        if not project_team_dto.team_id:
            team = await backend_sdk.create_team(project_team_dto.team_name)  # type: ignore
            project_team_dto.team_id = team["id"]
        await backend_sdk.create_project_application(project_team_dto)
        await message.answer(
            "Форма успешно отправлена! Спасибо за уделенное время",
            keyboard=GREETING_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error while sending application POST: {e}")
        await message.answer("Возникла техническая проблема, попробуйте снова позднее")
