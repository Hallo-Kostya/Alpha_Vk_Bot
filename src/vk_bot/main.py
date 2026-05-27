from src.common.logger import logger
from src.vk_bot.handlers import (
    greeting_labeler,
    form_labeler,
    edit_forms_labeler,
    interview_labeler,
)
from vkbottle import LoopWrapper
from src.vk_bot.bot import on_shutdown, on_startup, bot, chat_labeler


chat_labeler.load(greeting_labeler)
chat_labeler.load(form_labeler)
chat_labeler.load(edit_forms_labeler)
chat_labeler.load(interview_labeler)


if __name__ == "__main__":
    logger.info("Started VkBot")
    lw = LoopWrapper()
    lw.on_startup.append(on_startup())
    lw.on_shutdown.append(on_shutdown())
    bot.loop_wrapper = lw
    bot.run_forever()
