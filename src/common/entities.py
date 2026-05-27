from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class ProjectTeamMember:
    fullname: str
    role: str
    study_group: str

    def __str__(self):
        return f"{self.fullname}, {self.role}, {self.study_group}"


@dataclass(slots=True)
class ProjectTeam:
    project_id: UUID
    project_name: str
    vk_sender_id: int
    description: str | None = None
    team_name: str | None = None
    team_members: list[ProjectTeamMember] = field(default_factory=list)

    def __str__(self):
        return f"""\nКоманда: {self.team_name}

Описание: {self.description}

Выбранный проект: {self.project_name}

Данные участников команды:

{"\n".join(str(t_m) for t_m in self.team_members)}"""


@dataclass(slots=True)
class ProjectTeamMemberPATCH:
    fullname: str
    role: str
    study_group: str
    id: UUID | None = None

    def __str__(self):
        return f"{self.fullname}, {self.role}, {self.study_group}"


@dataclass(slots=True)
class ProjectTeamPATCH:
    project_id: UUID
    project_name: str
    vk_sender_id: int
    description: str = "Без описания"
    team_name: str | None = None
    team_members: list[ProjectTeamMemberPATCH] = field(default_factory=list)
    form_id: UUID | None = None

    def __str__(self):
        return f"""\nКоманда: {self.team_name}

Описание: {self.description}

Выбранный проект: {self.project_name}

Данные участников команды:

{"\n".join(str(t_m) for t_m in self.team_members)}"""
