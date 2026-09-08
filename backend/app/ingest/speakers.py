"""Speaker label resolution & normalization (docs/ARCHITECTURE.md §5.2).

Real transcript exports are inconsistent about how they name the same person
across cues — "Alex Kim", "alex kim", "ALEX", "Alex" all show up in the same
file. This module collapses those into one canonical participant per real
speaker using two safe, explainable rules (case-insensitive exact match, then
prefix match against the *longest* variant seen), not fuzzy matching that could
silently merge two different people who happen to share a first name.

Utterances with no speaker label at all (a bare plain-text paste) are grouped
under a single "Unknown speaker" participant rather than being split apart —
there is no signal to split them on, so guessing would be worse than one
honest bucket.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ingest.types import RawUtterance
from app.seed.seed import avatar_color_for

UNKNOWN_SPEAKER_LABEL = "Unknown speaker"


@dataclass
class ResolvedSpeaker:
    label: str  # canonical display name
    avatar_color: str


def _normalize_key(label: str) -> str:
    return " ".join(label.strip().split()).lower()


def resolve_speakers(utterances: list[RawUtterance]) -> dict[str, ResolvedSpeaker]:
    """Returns a map from each utterance's *raw* speaker_label (or
    UNKNOWN_SPEAKER_LABEL for None) to the ResolvedSpeaker it should be
    attributed to. Pass this straight to `normalizer.normalize` alongside the
    utterance list.
    """
    raw_labels = [u.speaker_label or UNKNOWN_SPEAKER_LABEL for u in utterances]

    # Group by normalized key first (case/whitespace-insensitive exact match).
    canonical_by_key: dict[str, str] = {}
    longest_by_key: dict[str, str] = {}
    for label in raw_labels:
        key = _normalize_key(label)
        if key not in longest_by_key or len(label) > len(longest_by_key[key]):
            longest_by_key[key] = label

    # Merge keys that are a strict prefix of a longer key's words (e.g. "alex"
    # is a word-prefix of "alex kim") — only when the prefix is itself a
    # standalone token boundary, never a substring mid-word.
    keys_by_word_count = sorted(longest_by_key.keys(), key=lambda k: -len(k.split()))
    merged_target: dict[str, str] = {}
    for short_key in sorted(longest_by_key.keys(), key=lambda k: len(k.split())):
        if short_key in merged_target:
            continue
        short_words = short_key.split()
        target = short_key
        for long_key in keys_by_word_count:
            if long_key == short_key or long_key in merged_target:
                continue
            long_words = long_key.split()
            if len(long_words) > len(short_words) and long_words[: len(short_words)] == short_words:
                target = long_key
                break
        merged_target[short_key] = target

    for key in longest_by_key:
        canonical_by_key[key] = longest_by_key[merged_target[key]]

    resolved: dict[str, ResolvedSpeaker] = {}
    for label in raw_labels:
        key = _normalize_key(label)
        canonical = canonical_by_key[key]
        if canonical not in resolved:
            resolved[canonical] = ResolvedSpeaker(
                label=canonical, avatar_color=avatar_color_for(canonical)
            )

    # Map every *original* raw label (not just the deduped set) to its resolved
    # speaker, so callers can look up by whatever the utterance actually carries.
    label_to_resolved: dict[str, ResolvedSpeaker] = {}
    for label in raw_labels:
        key = _normalize_key(label)
        label_to_resolved[label] = resolved[canonical_by_key[key]]
    return label_to_resolved
