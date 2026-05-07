from src.logger import logger
from src.bot import bot, chat_labeler
from src.handlers import greeting_labeler, form_labeler
from vkbottle import LoopWrapper
from src.bot import on_shutdown, on_startup


chat_labeler.load(greeting_labeler)
chat_labeler.load(form_labeler)


if __name__ == "__main__":
    logger.info("Started VkBot")
    lw = LoopWrapper()
    lw.on_startup.append(on_startup())
    lw.on_shutdown.append(on_shutdown())
    bot.loop_wrapper = lw
    bot.run_forever()
