"""Bounded noun-phrase and responsibility frames, not a general dependency parser.

Every frame consumes explicit syntax. Unknown list attachment fails closed;
responsibility never implies completion, ownership or a dependency edge.
"""
from __future__ import annotations

import re

from .models import Candidate

ROLES = r"engineer|researcher|scientist|professor|manager|director"
ACTIONS = r"building|preparing|testing|maintaining|operating|designing|manufacturing|supplying|supporting|managing"
# No conditional/relative/attributed scope may be silently erased by these frames.
UNSAFE = re.compile(
    r"\b(?:if|unless|but|except|although|whether|who|which|would|could|reportedly|"
    r"according to|claims?|said|says|hypothetical|fictional)\b", re.I)


def noun_list(text):
    """Explicit conjunction only, preserving full noun surfaces and rejecting clauses."""
    if re.search(r"\b(?:or|nor|not|never|is|was|were|are|may|might|will|has|have|had|"
                 r"from|since|until|through|during|in|on|at|by|with)\b", text, re.I):
        return None
    if "," in text and not re.search(r"\band\b", text):
        return None  # An unclosed list may contain an attachment we do not understand.
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
    values = []
    for part in parts:
        part = re.sub(r"^(?:the|a|an)\s+", "", part.strip())
        if (not re.fullmatch(r"[A-Za-z][\w'-]*(?:\s+[A-Za-z0-9][\w'-]*){0,7}", part)
                or len(part) > 160 or part.casefold() in {"it", "them", "this", "that", "they"}
                or UNSAFE.search(part)):
            return None
        values.append(part)
    return values if 1 <= len(values) <= 10 and len(set(values)) == len(values) else None


def responsibility_tasks(text):
    tasks = re.split(r",?\s+and for\s+", text)
    result = []
    for task in tasks:
        match = re.fullmatch(rf"(?P<action>{ACTIONS}) (?P<objects>.+)", task)
        if not match:
            return None
        objects, purpose = match["objects"], ""
        if " for " in objects:
            objects, purpose = objects.rsplit(" for ", 1)
            if (not re.fullmatch(r"[a-z]+(?: [a-z]+){0,2}", purpose) or UNSAFE.search(purpose)
                    or re.search(r"\b(?:not|no|never|may|might)\b", purpose)):
                return None
        names = noun_list(objects)
        if not names:
            return None
        predicate = "RESPONSIBLE_FOR_" + match["action"].upper()
        if purpose:
            predicate += "_FOR_" + purpose.upper().replace(" ", "_")
        if len(predicate) > 80:
            return None
        result.extend((predicate, name) for name in names)
    return result


def clause_candidates(evidence):
    """Return candidates plus whether an entire responsibility frame was consumed."""
    from .extract import NAME

    clause = evidence.rstrip(".!?").strip()
    if UNSAFE.search(clause):
        return [], False
    appositive = re.fullmatch(
        rf"(?P<s>{NAME}), (?:a|an) (?P<former>former )?(?P<org>{NAME}) "
        rf"(?P<role>{ROLES}), (?P<main>.+)", clause)
    additions = []
    if appositive:
        additions.append(Candidate(
            subject=appositive["s"].strip('"'), object=appositive["org"].strip('"'),
            predicate=("FORMER_" if appositive["former"] else "") + appositive["role"].upper() + "_AT",
            evidence=evidence, historical=bool(appositive["former"])))
    contractor = re.fullmatch(
        rf"(?P<s>{NAME}) (?P<aux>is|was) (?:the )?(?:main |primary |principal )?"
        rf"(?P<org>{NAME}) (?:industrial )?contractor, responsible for (?P<tasks>.+)", clause)
    direct = re.fullmatch(
        rf"(?P<s>{NAME}) (?P<aux>is|was|are|were|may be|might be|is not|was not|may not be|might not be) "
        r"responsible for (?P<tasks>.+)", clause)
    frame = contractor or direct
    if not frame:
        return additions, False
    tasks = responsibility_tasks(frame["tasks"])
    if tasks is None:
        return additions, False
    qualifiers = dict(historical=frame["aux"].startswith(("was", "were")),
                      polarity="negative" if "not" in frame["aux"] else "positive",
                      modality="possible" if frame["aux"].startswith(("may", "might")) else "asserted")
    subject = frame["s"].strip('"')
    if contractor:
        additions.append(Candidate(subject=subject, predicate="CONTRACTOR_FOR",
                                   object=contractor["org"].strip('"'), evidence=evidence, **qualifiers))
    additions.extend(Candidate(subject=subject, predicate=p, object=n,
                               evidence=evidence, **qualifiers) for p, n in tasks)
    return additions, True


def anchored_dates(subject, object_name, quote):
    """Recover only dates directly following this exact pair in one full quote.

    No scan for the first date in an entire paragraph; initials in literal entity
    names are allowed without changing the existing sentence/event segmenter.
    """
    from .extract import TEMPORAL_TAIL, temporal

    match = re.fullmatch(re.escape(subject) + r"\s+(?P<link>[a-z -]{1,80}?)\s+"
                         + r"(?:the |a |an )?" + re.escape(object_name)
                         + "(?P<time>" + TEMPORAL_TAIL.pattern + r")[.!?]?", quote)
    if not match:
        return {}
    fields = temporal(match["time"])
    if re.search(r"\b(?:was|were|served|worked|managed|operated|led)\b", match["link"]):
        fields["historical"] = True
    return fields


def entity_hints(text):
    """Bounded source-only surface/offset hints; no gold labels or invented aliases."""
    from .extract import NAME, SENTENCE

    names = {m[0].strip('"') for m in re.finditer(NAME, text)}
    for sentence in SENTENCE.finditer(text):
        additions, _ = clause_candidates(sentence[0].strip())
        names.update(n for c in additions for n in (c.subject, c.object))
    rows = []
    for name in sorted(names, key=lambda n: (text.find(n), n)):
        if name in {"The", "A", "An", "We", "It", "He", "She", "They", "Ignore"}:
            continue
        start = text.find(name)
        if start >= 0:
            rows.append(dict(text=name, start=start, end=start + len(name)))
        if len(rows) == 24:
            break
    return rows
