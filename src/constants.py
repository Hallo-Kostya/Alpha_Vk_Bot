from dotenv import load_dotenv
import os

load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
IS_DEV: bool = bool(os.getenv("IS_DEV", 0))
BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://localhost:8001/api/v1")


class BotSettings:
    base_greeting: str = """
Привет!
Я чат-бот для записи на проекты Альфа Банка в рамках Проектного Практикума УрФУ.
Чем я могу Вам помочь?
"""

