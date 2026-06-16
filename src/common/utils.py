from vkbottle import Keyboard, Text, KeyboardButtonColor
from vkbottle.bot import Message
from src.common.logger import logger


def build_keyboard(buttons: list[tuple], one_time: bool = True, inline: bool = False):
    keyboard = Keyboard(one_time=one_time, inline=inline)

    for index, (name, payload) in enumerate(buttons, 1):
        if index % 4 == 0:
            keyboard.row()
        keyboard.add(
            Text(
                name,
                payload=payload,
            ),
            color=KeyboardButtonColor.PRIMARY,
        )

    return keyboard


def format_team(team: dict) -> str:
    lines = []

    lines.append(f"Команда: {team.get('name')}")

    members = team.get("members") or []

    lines.append("\nУчастники:")

    for m in members:
        student = m.get("student") or {}

        last_name = student.get("last_name")
        first_name = student.get("first_name")
        patronymic = student.get("patronymic")

        fio = " ".join(filter(None, [last_name, first_name, patronymic]))

        role = m.get("role") or "—"
        group = m.get("study_group") or "—"

        lines.append(f"- {fio}, Роль: {role}, Академическая группа: {group}")

    return "\n".join(lines)


async def validate_payload(message: Message) -> dict | None:
    if not message.state_peer or "project_team" not in message.state_peer.payload:
        logger.error(
            f"Error while handling team name: incorrect payload: {message.state_peer}"
        )
        await message.answer(
            "Возникли проблемы с выбором проекта, повторите попытку позднее, пожалуйста"
        )
        return None
    return message.state_peer.payload


def format_name_for_button(name: str) -> str:
    if len(name) >= 40:
        return name[:39]
    return name
