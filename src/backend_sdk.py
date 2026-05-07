from src.http_client import HttpClient
from src.constants import BackendConfig
import asyncio
from src.logger import logger
from datetime import datetime, timezone
from src.exceptions import BackendNotAvailable
from uuid import UUID
from src.entities import ProjectTeam, ProjectTeamMember


class BackendSdk:
    def __init__(self, http_client: HttpClient):
        self._http_client = http_client
        self._base_url = BackendConfig.api_url
        self.__access_token: dict = {}
        self.__refresh_token: dict = {}
        self._auth_headers = BackendConfig.auth_headers
        self._auth_lock = asyncio.Lock()

    async def _auth(self):
        logger.info("Authenticating...")
        data = {
            "email": BackendConfig.service_email,
            "password": BackendConfig.service_pass,
        }
        url = f"{self._base_url}/auth/login"
        response_json = await self._http_client.post(url, json=data)
        if not isinstance(response_json, dict):
            raise BackendNotAvailable
        self._set_auth_tokens(response_json)

    async def _refresh_tokens(self) -> None:
        logger.info("Refreshing tokens...")
        data = {"refresh": self.__refresh_token}
        url = f"{self._base_url}/auth/refresh"
        response_json = await self._http_client.post(url, json=data)
        if not isinstance(response_json, dict):
            raise BackendNotAvailable
        self._set_auth_tokens(response_json)

    def _set_auth_tokens(self, data: dict) -> None:
        self.__access_token = data["access_token"]
        self.__refresh_token = data["refresh_token"]
        access_expires_at = self.__access_token["expires_at"]
        refresh_expires_at = self.__refresh_token["expires_at"]
        self.__access_token["expires_at"] = datetime.strptime(
            access_expires_at, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)
        self.__refresh_token["expires_at"] = datetime.strptime(
            refresh_expires_at, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)
        self._auth_headers["Authorization"] = self._auth_headers[
            "Authorization"
        ].format(token=self.__access_token["token"])

    def _is_token_actual(self, expires_date: datetime) -> bool:
        return datetime.now(tz=timezone.utc) >= expires_date

    async def _ensure_tokens(self) -> None:
        async with self._auth_lock:
            if not self.__refresh_token or not self._is_token_actual(
                self.__refresh_token["expires_at"]
            ):
                return await self._auth()
            if not self._is_token_actual(self.__access_token["expires_at"]):
                return await self._refresh_tokens()

    async def get_available_projects_for_user(self, vk_user_id: int) -> list[dict]:
        await self._ensure_tokens()
        url = f"{self._base_url}/project_applications/{vk_user_id}/available_projects"
        response = await self._http_client.get(
            url, headers=self._auth_headers,
        )
        if not isinstance(response, list):
            raise BackendNotAvailable
        return response
        

    async def create_project_application(self, project_form: ProjectTeam) -> None:
        if not project_form.team_name:
            print("govno")
            return
        for team_member in project_form.form_members:
            student = await self.create_student(team_member.fullname)
            student_id = student.get("id")
            if not student_id or not project_form.team_id:
                print("govno2")
                return
            await self.add_student_to_team(project_form.team_id, student_id, team_member.project_role, team_member.academic_group)
        await self.send_project_form({"project_id": project_form.project_id, "team_id": project_form.team_id, "vk_sender_id": project_form.vk_sender_id})


    async def add_student_to_team(self, team_id: UUID, student_id: UUID, role: str, study_group: str) -> dict:
        await self._ensure_tokens()
        url = f"{self._base_url}/teams/{team_id}/students"
        data = {
            "student_id": student_id,
            "role": role,
            "study_group": study_group
        }
        response = await self._http_client.post(
            url, headers=self._auth_headers, json=data
        )
        if not isinstance(response, dict):
            raise BackendNotAvailable
        return response


    async def send_project_form(self, project_form: dict) -> dict: #TODO
        await self._ensure_tokens()
        url = f"{self._base_url}/project_applications/"
        logger.info(project_form)
        response = await self._http_client.post(
            url, headers=self._auth_headers, json=project_form
        )
        if not isinstance(response, dict):
            raise BackendNotAvailable
        return response
    
    async def create_team(self, team_name: str) -> dict:
        await self._ensure_tokens()
        url = f"{self._base_url}/teams/"
        response = await self._http_client.post(
            url, headers=self._auth_headers, json={"name": team_name}
        )
        if not isinstance(response, dict):
            raise BackendNotAvailable
        return response
    
    async def create_student(self, full_name: str) -> dict:
        await self._ensure_tokens()
        url = f"{self._base_url}/students/"
        name_parts = full_name.split(" ")
        data = {
            "last_name": name_parts[0],
            "first_name": name_parts[1],
            "patronymc": name_parts[2] if len(name_parts) > 2 else None,
        }
        response = await self._http_client.post(
            url, headers=self._auth_headers, json=data
        )
        if not isinstance(response, dict):
            raise BackendNotAvailable
        return response
    
    async def create_team_member(self, full_name: str) -> dict:
        await self._ensure_tokens()
        url = f"{self._base_url}/students/"
        name_parts = full_name.split(" ")
        data = {
            "last_name": name_parts[0],
            "first_name": name_parts[1],
            "patronymc": name_parts[2] if len(name_parts) > 2 else None,
        }
        response = await self._http_client.post(
            url, headers=self._auth_headers, json=data
        )
        if not isinstance(response, dict):
            raise BackendNotAvailable
        return response

    async def get_peer_project_forms(self, sender_id: int) -> list[dict]: #TODO
        await self._ensure_tokens()
        url = f"{self._base_url}/project_applications/"
        params = {
            "vk_sender_id": sender_id,
        }
        response = await self._http_client.get(
            url, headers=self._auth_headers, params=params
        )
        if not isinstance(response, list):
            raise BackendNotAvailable
        return response

    async def get_teams(self, team_name: str | None = None, vk_peer_id: int | None = None) -> list[dict]:
        if not (team_name or vk_peer_id):
            logger.error("None of required args (team_name, vk_peer_id) is passed in get team method")
            return []
        await self._ensure_tokens()
        url = f"{self._base_url}/teams/detailed_list"
        params: dict[str, int | str] = {}
        if team_name:
            params["name"] = team_name
        if vk_peer_id:
            params["vk_sender_id"] = vk_peer_id
        response = await self._http_client.get(
            url, headers=self._auth_headers, params=params
        )
        if not isinstance(response, list):
            raise BackendNotAvailable
        return response
