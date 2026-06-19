from pydantic import BaseModel


class TaskIn(BaseModel):
    title: str
    category: str = ""
    type: str = ""          # accepts API ("major"/"d2d") or stored ("Major"/"Day to Day")
    date: str = ""          # "" = open task, "YYYY-MM-DD" = begin date


class TaskPatch(BaseModel):
    title: str | None = None
    category: str | None = None
    type: str | None = None
    date: str | None = None
    blocked_by: str | None = None   # comma-separated blocker task ids ("" clears)


class SubtaskIn(BaseModel):
    title: str


class UpdateIn(BaseModel):
    text: str


class EventIn(BaseModel):
    title: str
    single: bool = True
    start: str
    end: str = ""
    comment: str = ""       # optional first comment


class EventPatch(BaseModel):
    title: str | None = None
    single: bool | None = None
    start: str | None = None
    end: str | None = None


class NameIn(BaseModel):
    name: str


class RenameIn(BaseModel):
    old: str
    new: str
