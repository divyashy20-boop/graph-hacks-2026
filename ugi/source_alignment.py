"""Optional, strictly textual evidence realignment.

This helper never establishes semantics, identity or provenance. It can only
recover a UNIQUE exact slice of the original source when differences are
limited to Unicode whitespace. Original bytes/characters win.
"""
from __future__ import annotations


def _collapse_with_offsets(text: str):
    output = []
    positions = []
    # Collapse each whitespace run into a single space, mapping to original.
    for i, char in enumerate(text):
        if char.isspace():
            if output and output[-1] == " ":
                continue
            output.append(" ")
            positions.append(i)
        else:
            output.append(char)
            positions.append(i)
    return "".join(output), positions


def align_exact_evidence(source: str, proposal: str) -> str | None:
    """Return an exact source substring only for a unique whitespace-equivalent match.

    This does *not* correct typos, mojibake, paraphrases, changed punctuation,
    omitted qualifiers, or misidentified entities.
    """
    if not source or not proposal or len(proposal) > 4000:
        return None
    if proposal in source:
        return proposal
    normalized, offsets = _collapse_with_offsets(source)
    quote, _ = _collapse_with_offsets(proposal)
    quote = quote.strip()
    if not quote or quote not in normalized:
        return None
    start = normalized.find(quote)
    if normalized.find(quote, start + 1) >= 0:
        return None
    end = start + len(quote)
    # Ignore collapsed surrounding whitespace; return original exact source slice.
    original = source[offsets[start]:offsets[end - 1] + 1]
    if len(original) > 4000 or _collapse_with_offsets(original)[0].strip() != quote:
        return None
    return original
