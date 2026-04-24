"""Split text into sentences for streaming TTS."""

import re

# Common abbreviations that should NOT trigger a sentence break.
_ABBREVIATIONS = frozenset([
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "ave", "blvd",
    "dept", "est", "vol", "vs", "inc", "ltd", "corp", "co", "no",
    "approx", "govt", "etc", "e.g", "i.e",
])

# Sentence-ending punctuation followed by whitespace or end-of-string.
_SENTENCE_BOUNDARY = re.compile(
    r'(?<=[.!?…])'   # lookbehind: sentence-ending punctuation
    r'(?:\s+)'        # one or more whitespace characters
    r'(?=[A-Z0-9"\'(])',  # lookahead: next sentence starts with uppercase, digit, or quote
    re.UNICODE,
)


def split_sentences(text: str) -> list[str]:
    """Return a list of non-empty sentence strings from *text*.

    Handles common abbreviations (Mr., Dr., etc.), decimal numbers,
    and ellipses so they do not cause false splits.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    # Split on sentence boundaries.
    raw_parts = _SENTENCE_BOUNDARY.split(cleaned)

    sentences: list[str] = []
    buffer = ""

    for part in raw_parts:
        stripped = part.strip()
        if not stripped:
            continue

        candidate = f"{buffer} {stripped}".strip() if buffer else stripped

        # Check if the candidate ends with an abbreviation followed by a period.
        last_word = candidate.rstrip(".!?…").rsplit(None, 1)[-1].lower() if candidate else ""
        if last_word in _ABBREVIATIONS and candidate.endswith("."):
            buffer = candidate
            continue

        buffer = ""
        sentences.append(candidate)

    # Flush anything remaining in the buffer.
    if buffer.strip():
        sentences.append(buffer.strip())

    return sentences if sentences else [cleaned]
