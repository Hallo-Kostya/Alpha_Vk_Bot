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
