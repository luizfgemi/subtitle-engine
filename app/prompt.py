"""Load and render the immutable prompt selected for translation."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files

PROMPT_ID = "translategemma-v1"
PROMPT_TEMPLATE = (
    files("app.prompts").joinpath(f"{PROMPT_ID}.txt").read_text(encoding="utf-8").rstrip("\n")
)
PROMPT_SHA256 = sha256(PROMPT_TEMPLATE.encode()).hexdigest()


def render_prompt(
    *, source_name: str, source_code: str, target_name: str, target_code: str, text: str
) -> str:
    """Render the selected template without modifying the source text."""
    return PROMPT_TEMPLATE.format(
        source_name=source_name,
        source_code=source_code,
        target_name=target_name,
        target_code=target_code,
        text=text,
    )
