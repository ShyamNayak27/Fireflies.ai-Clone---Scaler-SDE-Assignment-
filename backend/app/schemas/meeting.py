"""Pydantic request/response schemas — the API's actual contract (also what
FastAPI turns into the OpenAPI doc)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    avatar_color: str
    is_host: bool


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    started_at: str
    duration_ms: int
    status: str
    participants: list[ParticipantOut] = []
    tags: list[TagOut] = []


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    next_cursor: str | None


class MeetingDetail(MeetingListItem):
    description: str | None
    media_url: str | None
    media_type: str | None
    timestamps_estimated: bool


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    idx: int
    start_ms: int
    end_ms: int
    text: str
    speaker: ParticipantOut | None = None


class TranscriptResponse(BaseModel):
    items: list[SegmentOut]
    next_cursor: str | None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    text: str
    start_ms: int | None


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    start_ms: int
    end_ms: int
    notes: list[NoteOut] = []


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    overview: str
    model: str | None
    generated_at: str
    chapters: list[ChapterOut] = []


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    completed: bool
    due_date: str | None
    assignee: ParticipantOut | None = None
    source_segment_id: int | None


class ActionItemCreate(BaseModel):
    text: str
    assignee_id: int | None = None
    due_date: str | None = None
    source_segment_id: int | None = None


class ActionItemUpdate(BaseModel):
    text: str | None = None
    completed: bool | None = None
    due_date: str | None = None
    assignee_id: int | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskCitationOut(BaseModel):
    number: int
    segment_id: int
    start_ms: int


class AskResponse(BaseModel):
    answer: str
    citations: list[AskCitationOut]
    model: str | None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    segment_id: int
    body: str
    created_at: str


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class HighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    segment_id: int
    color: str
    start_offset: int
    end_offset: int


class HighlightCreate(BaseModel):
    color: str = Field(default="yellow", max_length=20)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class SoundbiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    start_ms: int
    end_ms: int


class SoundbiteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class SearchHit(BaseModel):
    meeting_id: int
    meeting_title: str
    segment_id: int
    start_ms: int
    speaker_name: str | None
    snippet: str


class SearchResponse(BaseModel):
    items: list[SearchHit]
