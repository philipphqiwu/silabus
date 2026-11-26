"""Turn a source's HTML-ish description into plain text.

Sources ship markup in different shapes: Greenhouse escapes its HTML twice,
Lever and friends do not. Unescape first, then remove the markup. Boilerplate
("About us", "Apply now", equal opportunity statements) is left alone for now;
it needs a real sample to tune against, and guessing at it here would just move
noise from one place to another.
"""

from __future__ import annotations

import html
import re

MAX_CHARS = 20_000

_SCRIPT_OR_STYLE = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
_BLOCK_TAG = re.compile(
    r"(?i)</?(p|div|br|li|ul|ol|h[1-6]|tr|td|section|article|blockquote)\b[^>]*>"
)
_ANY_TAG = re.compile(r"(?s)<[^>]{0,400}>")
_HORIZONTAL_WS = re.compile(r"[ \t\u00a0]+")


def clean_description(raw: str | None) -> str:
    if not raw:
        return ""

    text = html.unescape(raw)
    text = _SCRIPT_OR_STYLE.sub(" ", text)
    text = _BLOCK_TAG.sub("\n", text)
    text = _ANY_TAG.sub(" ", text)
    text = html.unescape(text)
    text = _HORIZONTAL_WS.sub(" ", text)
    # Blank lines carry no meaning for extraction, so they are dropped and each
    # block ends up on its own line.
    lines = (line.strip() for line in text.splitlines())
    text = "\n".join(line for line in lines if line)
    return text[:MAX_CHARS]
