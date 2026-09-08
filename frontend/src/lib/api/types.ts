// Mirrors backend/app/schemas/meeting.py — the two are the same contract by hand
// today; docs/ARCHITECTURE.md §6.1 notes generating this from the OpenAPI schema
// as a follow-up once the surface stabilizes.

export interface Participant {
  id: number;
  name: string;
  avatar_color: string;
  is_host: boolean;
}

export interface Tag {
  id: number;
  name: string;
}

export interface MeetingListItem {
  id: number;
  title: string;
  started_at: string;
  duration_ms: number;
  status: "processing" | "ready" | "failed";
  participants: Participant[];
  tags: Tag[];
}

export interface MeetingListResponse {
  items: MeetingListItem[];
  next_cursor: string | null;
}

export interface MeetingDetail extends MeetingListItem {
  description: string | null;
  media_url: string | null;
  media_type: "audio" | "video" | null;
  timestamps_estimated: boolean;
}

export interface Segment {
  id: number;
  idx: number;
  start_ms: number;
  end_ms: number;
  text: string;
  speaker: Participant | null;
}

export interface TranscriptResponse {
  items: Segment[];
  next_cursor: string | null;
}

export interface Note {
  text: string;
  start_ms: number | null;
}

export interface Chapter {
  title: string;
  start_ms: number;
  end_ms: number;
  notes: Note[];
}

export interface Summary {
  overview: string;
  model: string | null;
  generated_at: string;
  chapters: Chapter[];
}

export interface ActionItem {
  id: number;
  text: string;
  completed: boolean;
  due_date: string | null;
  assignee: Participant | null;
  source_segment_id: number | null;
}

export interface ActionItemCreate {
  text: string;
  assignee_id?: number | null;
  due_date?: string | null;
  source_segment_id?: number | null;
}

export interface ActionItemUpdate {
  text?: string;
  completed?: boolean;
  due_date?: string | null;
  assignee_id?: number | null;
}

export interface JobOut {
  id: string;
  type: "ingest" | "summarize";
  status: "queued" | "running" | "succeeded" | "failed";
  stage: string | null;
  progress: number;
  error: string | null;
  meeting_id: number | null;
}

export interface AskCitation {
  number: number;
  segment_id: number;
  start_ms: number;
}

export interface AskResponse {
  answer: string;
  citations: AskCitation[];
  model: string | null;
}

export interface SearchHit {
  meeting_id: number;
  meeting_title: string;
  segment_id: number;
  start_ms: number;
  speaker_name: string | null;
  snippet: string;
}
