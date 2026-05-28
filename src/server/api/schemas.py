from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


class NotifyDeclineAccept(BaseModel):
    team_name: str
    project_name: str


class InterviewPossibleDates(BaseModel):
    possible_dates: list[datetime]
    team_name: str
    project_name: str
    application_id: UUID


class InterviewUpdate(BaseModel):
    team_name: str
    project_name: str
    url: str | None = None
    date: datetime | None = None

    @model_validator(mode="after")
    def check_url_or_date(self):
        if self.url is None and self.date is None:
            raise ValueError("Either url or date must be provided")
        return self
