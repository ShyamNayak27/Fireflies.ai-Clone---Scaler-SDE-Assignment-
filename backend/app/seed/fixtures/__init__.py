from typing import Any

from app.seed.fixtures.meeting_01_morning_standup import MEETING as MORNING_STANDUP
from app.seed.fixtures.meeting_02_onboarding import MEETING as ONBOARDING
from app.seed.fixtures.meeting_03_technical_sync import MEETING as TECHNICAL_SYNC
from app.seed.fixtures.meeting_04_investor_pitch import MEETING as INVESTOR_PITCH
from app.seed.fixtures.meeting_05_customer_interview import MEETING as CUSTOMER_INTERVIEW
from app.seed.fixtures.meeting_06_retro import MEETING as RETRO

# Each MEETING is a hand-written, deliberately heterogeneous literal (strings,
# nested dicts, lists of dicts) — a TypedDict per fixture would be more
# precise but these are one-off seed data, not a runtime API contract, so
# `dict[str, Any]` here (rather than sprinkling `Any`/`cast` through
# seed.py's consumption of it) is the appropriately-scoped fix.
ALL_MEETINGS: list[dict[str, Any]] = [
    MORNING_STANDUP,
    ONBOARDING,
    TECHNICAL_SYNC,
    INVESTOR_PITCH,
    CUSTOMER_INTERVIEW,
    RETRO,
]
