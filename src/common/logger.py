import logging
from src.common.constants import IS_DEV

logger = logging.getLogger("vkbottle")
level = logging.INFO
if IS_DEV:
    level = logging.DEBUG
logger.setLevel(level)
