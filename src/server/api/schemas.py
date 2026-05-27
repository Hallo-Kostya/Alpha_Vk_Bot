from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotifyDeclineAccept(BaseModel):
    team_name: str
    project_name: str


class InterviewPossibleDates(BaseModel):
    possible_dates: list[datetime]
    team_name: str
    project_name: str
    application_id: UUID
