from src.logger import logger
from src.bot import bot, chat_labeler
from src.handlers import greeting_labeler, form_labeler

chat_labeler.load(greeting_labeler)
chat_labeler.load(form_labeler)


if __name__ == "__main__":
    logger.info("Started VkBot")
    bot.run_forever()
