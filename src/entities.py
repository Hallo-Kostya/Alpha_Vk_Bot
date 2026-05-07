from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class ProjectTeamMember:
    fullname: str
    project_role: str
    academic_group: str

    def __str__(self):
        return f"{self.fullname}, {self.project_role}, {self.academic_group}"


@dataclass(slots=True)
class ProjectTeam:
    project_id: UUID
    project_name: str
    vk_sender_id: int
    team_id: UUID | None = None
    team_name: str | None = None
    form_members: list[ProjectTeamMember] = field(default_factory=list)

    def __str__(self):
        return f"""\nКоманда: {self.team_name}

Выбранный проект: {self.project_name}

Данные участников команды:

{"\n".join(str(t_m) for t_m in self.form_members)}"""