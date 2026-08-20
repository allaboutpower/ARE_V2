import datetime

from pydantic import BaseModel, ConfigDict


class WeekOption(BaseModel):
    week_index: int
    week_date: str


class WeeksResponse(BaseModel):
    filename: str
    weeks: list[WeekOption]


class PromptCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    week_index: int
    week_date: str
    evidence_package: dict
    prompt_text: str
    created_at: datetime.datetime


class PromptListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    week_index: int
    week_date: str
    created_at: datetime.datetime
