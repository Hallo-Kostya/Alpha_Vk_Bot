from dotenv import load_dotenv
import os

load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
IS_DEV: bool = bool(os.getenv("IS_DEV", 0))
HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", 20))

FORM_STATUSES_MAPPING: dict = {
    "UNSEEN": "На согласовании",
    "DECLINED": "Отклонена",
    "ACCEPTED": "Согласована",
    "WAITING_FOR_ACK": "Ждёт оценки",
    "INTERVIEW": "Назначено интервью",
}

INTERVIEW_STATUSES_MAPPING: dict = {
    "NEW": "Ждём согласования времени от кураторов",
    "WAITING": "Интервью согласовано",
    "RATING": "Ждём оценки от кураторов",
    "RATED": "Интервью оценено",
    "CANCELED": "Интервью отменено",
}


class BotSettings:
    base_greeting: str = """
Привет!
Я чат-бот для записи на проекты Альфа Банка в рамках Проектного Практикума УрФУ.
Через меня вы можете:
- Отправить/изменить заявки на открытые в этом семестре проекты
- Назначить собеседование, после одобрения заявки с нашей стороны
- И просто узнать получше об открытых проектах

Чем я могу Вам помочь?
"""
    find_team_retries: int = 5
    edit_team_members_template: str = """
Пожалуйста, напишите Фамилию, Имя, Отчество (при наличии) всех участников Вашей команды, а также их роли и академические группы через запятую.
Каждого участника, пожалуйста, вводите с новой строки.
Общий формат должен получиться такой:

Иванов Иван Иванович, дизайнер, РИ-111111
Дмитриев Дмитрий, бекендер, РИ-123456
Бурдук Константин Евгеньевич, фронтендер, РИ-123456
Воронцов Тимофей Григорьевич, аналитик, РИ-123020
Андреев Иван Максимович, тимлид, РИ-330943

"""


class BackendConfig:
    api_url: str = os.getenv("BACKEND_API_URL", "http://host.docker.internal:8001/api")
    service_email: str = os.getenv("BACKEND_SERVICE_ACNT_EMAIL", "")
    service_pass: str = os.getenv("BACKEND_SERVICE_ACNT_PASS", "")
    auth_headers: dict = {"Authorization": "Bearer {token}"}


class ServerConfig:
    hash_secret: str = os.getenv("SERVER_HASH_SECRET", "")
    hash_algorithm: str = os.getenv("SERVER_HASH_ALGORITHM", "")
    services_whitelist: set[str] = set(
        os.getenv("SERVER_SERVICES_WHITELIST", "alpha_back").split(",")
    )
