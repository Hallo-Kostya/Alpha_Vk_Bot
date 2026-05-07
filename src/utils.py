from vkbottle import Keyboard, Text, KeyboardButtonColor


def build_keyboard(buttons: list[tuple], one_time: bool = True, inline: bool = False):
    keyboard = Keyboard(one_time=one_time, inline=inline)

    for name, payload in buttons:
        keyboard.add(
            Text(
                name,
                payload=payload,
            ),
            color=KeyboardButtonColor.PRIMARY
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