from dotenv import load_dotenv
import os

load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
IS_DEV: bool = bool(os.getenv("IS_DEV", 0))
HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", 20))

FORM_STATUSES_MAPPING: dict = {
    "NEW": "Ждёт обработки",
    "DECLINED": "Отклонена",
    "ACCEPTED": "Принята",
    "PENDING": "В обработке",
}

class BotSettings:
    base_greeting: str = """
Привет!
Я чат-бот для записи на проекты Альфа Банка в рамках Проектного Практикума УрФУ.
Чем я могу Вам помочь?
"""


class BackendConfig:
    api_url: str = os.getenv("BACKEND_API_URL", "http://localhost:8001/api")
    service_email: str = os.getenv("BACKEND_SERVICE_ACNT_EMAIL", "")
    service_pass: str = os.getenv("BACKEND_SERVICE_ACNT_PASS", "")
    auth_headers: dict = {
        "Authorization": "Bearer {token}"
    }
