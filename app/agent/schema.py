from pydantic import BaseModel, Field
from enum import Enum


class EventType(Enum):
    event = "event"
    reminder = "reminder"
    unknown = "unknown"


class FrequencyType(Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class WeekdayType(Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class Recurrence(BaseModel):
    frequency: FrequencyType
    interval: int | None = None
    weekdays: list[WeekdayType] | None = None
    ordinal: int | None = None
    month_day: int | None = None
    until: int | None = None


class ParsedItem(BaseModel):
    type: EventType
    title: str | None = None
    description: str | None = None
    date: str | None = None
    time: str | None = None
    timezone: str | None = None
    is_all_day: bool | None = None
    confidence: float = Field(ge=0, le=1)
    clarification_question: str | None = None
    recurrence: Recurrence | None = None
