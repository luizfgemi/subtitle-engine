"""Conservative heuristics for auditing generated subtitle translations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.srt import SrtCue, strip_styles

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
ENGLISH_MARKERS = frozenset(
    "the an and but or if then this that these those is are was were be been "
    "have has had does did not you your he she it we they his her their "
    "what when where why how with from for until before after can could would "
    "should will just don't doesn't didn't i'm you're he's she's we're they're"
    .split()
)
PORTUGUESE_MARKERS = frozenset(
    "o a os as um uma e mas ou se então este esta isso aquilo é são era eram "
    "ser ter tem tinha não você vocês ele ela nós eles seu sua dele dela que "
    "quando onde por porque como com de para até antes depois posso pode poderia"
    .split()
)


@dataclass(frozen=True)
class AuditIssue:
    kind: str
    timestamp: str
    source: str
    translated: str


def _plain(text: str) -> str:
    return strip_styles(text)[0].replace("\n", " ").strip()


def _words(text: str) -> list[str]:
    return [word.casefold() for word in WORD_RE.findall(_plain(text))]


def audit_cues(source: list[SrtCue], translated: list[SrtCue]) -> list[AuditIssue]:
    """Return high-signal warnings without claiming semantic correctness."""
    translated_by_timestamp = {cue.timestamp: cue for cue in translated}
    issues: list[AuditIssue] = []
    previous: tuple[str, str] | None = None

    for source_cue in source:
        target_cue = translated_by_timestamp.get(source_cue.timestamp)
        if target_cue is None:
            issues.append(AuditIssue("missing", source_cue.timestamp, source_cue.text, ""))
            continue

        source_text = _plain(source_cue.text)
        target_text = _plain(target_cue.text)
        source_words = _words(source_text)
        target_words = _words(target_text)

        source_english = sum(word in ENGLISH_MARKERS for word in source_words)
        if (
            len(source_words) >= 3
            and source_english
            and source_text.casefold() == target_text.casefold()
        ):
            issues.append(AuditIssue("unchanged", source_cue.timestamp, source_cue.text, target_cue.text))
        elif len(target_words) >= 4:
            english = sum(word in ENGLISH_MARKERS for word in target_words)
            portuguese = sum(word in PORTUGUESE_MARKERS for word in target_words)
            if english >= 2 and english > portuguese * 2:
                issues.append(AuditIssue("english", source_cue.timestamp, source_cue.text, target_cue.text))

        if len(source_words) >= 8 and len(target_words) * 3 < len(source_words):
            issues.append(AuditIssue("truncated", source_cue.timestamp, source_cue.text, target_cue.text))

        normalized_target = " ".join(target_words)
        normalized_source = " ".join(source_words)
        if (
            previous
            and len(target_words) >= 3
            and normalized_target == previous[1]
            and normalized_source != previous[0]
        ):
            issues.append(AuditIssue("repeated", source_cue.timestamp, source_cue.text, target_cue.text))
        previous = normalized_source, normalized_target

    return issues
