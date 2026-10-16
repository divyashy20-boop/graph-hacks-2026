"""Bounded literal open frames, not a learned OpenIE model or truth verifier."""
import re

from .models import Candidate, EventParticipant, RelationEventCandidate, key

VERSION = "literal-open-frames-v1"
SCOPE = re.compile(r"\b(proposed|planned|attempted|failed|cancelled|canceled|may|might|not|never)\b", re.I)


def scope(phrase, evidence):
    markers = sorted(set(m[0].lower() for m in SCOPE.finditer(phrase)))
    cancelled = bool(re.search(r"\b(?:cancelled|canceled)\b", evidence, re.I))
    amounts = re.findall(r"\$\d+(?:\.\d+)?(?: million| billion)?", evidence)
    return dict(modifiers=markers, lifecycle="cancelled" if cancelled else "unspecified",
                amounts=amounts, semantics="Literal source qualifiers, not transaction completion")


def extract_open(text):
    from .extract import NAME, SENTENCE, TEMPORAL_TAIL, temporal

    binaries, events = [], []
    def names(value):
        parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", value)
        return parts if 1 <= len(parts) <= 6 and all(re.fullmatch(NAME, p) for p in parts) else []

    def participant(role, name):
        return EventParticipant(role=role, name=name.strip('"'))

    for sentence in list(SENTENCE.finditer(text))[:60]:
        evidence = sentence[0].strip()
        clause = evidence.rstrip(".!?").strip()
        if len(clause) > 1200 or re.search(
                r"\b(?:if|unless|whether|said|says|claimed|according to|reportedly)\b", clause, re.I):
            continue
        dates = temporal(evidence)
        year = re.search(r"\bin (\d{4})\b", evidence)
        if year and not any(f in dates for f in ("event_time", "valid_from", "valid_to")):
            dates.update(event_time=year[1]+"-01-01", time_precision="year", temporal_source=year[0], historical=True)
        offset = sentence.start() + len(sentence[0])-len(sentence[0].lstrip())
        # Aligned lists are distributive only when 'respectively' is explicit.
        if "respectively" in clause:
            m = re.fullmatch(r"(.+?) (acquired|bought|purchased) (.+?) respectively", clause)
            if m:
                left, right = names(m[1]), names(m[3])
                if 2 <= len(left) == len(right) <= 6:
                    binaries.extend(Candidate(subject=a.strip('"'), predicate=m[2], object=b.strip('"'),
                                              evidence=evidence, **dates) for a,b in zip(left,right,strict=True))
            continue  # Never fallback to all-to-all or partial pairing.
        group = re.fullmatch(r"(.+?) (collaborated|partnered) with (.+?) on (.+)", clause)
        research = re.fullmatch(r"Researchers (.+?) jointly investigated (?:the relationship between )?(.+?)(?: at (.+))?", clause)
        if group:
            left, right = names(group[1]), names(group[3])
            project = names(group[4])
            if not left or not right or len(project) != 1 or len(left)+len(right)+1 > 12:
                continue
            participants = [*[participant("collaborator", n) for n in left],
                            *[participant("partner", n) for n in right], participant("project", project[0])]
            phrase = group[2] + " with"
        elif research:
            people, topics = names(research[1]), names(research[2])
            orgs = names(research[3]) if research[3] else []
            if not people or not topics or (research[3] and len(orgs) != 1):
                continue
            participants = [*[participant("researcher", n) for n in people],
                            *[participant("topic", n) for n in topics],
                            *[participant("institution", n) for n in orgs]]
            phrase = "jointly investigated"
        else:
            participants = None
        if participants:
            if 3 <= len(participants) <= 12:
                events.append(RelationEventCandidate(relation_type=phrase, participants=participants,
                              evidence=evidence, evidence_start=offset, **dates))
            continue
        # Coordination not captured above is ambiguous; do not create a binary
        # projection or discard a trailing participant silently.
        if re.search(r"\b(?:and|or|jointly|collaborated|partnered)\b", clause):
            continue
        m = re.fullmatch(rf"(?P<s>{NAME}) (?P<neg>does not |did not |never )?"
                         r"(?P<modal>may |might |allegedly )?(?P<modalneg>not )?"
                         rf"(?P<p>[a-z][a-z -]{{0,90}}?) (?P<o>{NAME})(?P<tail>.*)", clause)
        if not m or key(m["s"]) in {"he","she","it","they","this","that"}:
            continue
        phrase, tail = m["p"].strip(), m["tail"]
        if (len(phrase.split()) > 10 or len(phrase) > 80
                or re.match(r"^(?:is|was|are|were) (?:a|an|the)\b", phrase)
                or phrase in {"is","was","and","or","said","mentioned","compared with"}
                or (m["modalneg"] and not m["modal"])):
            continue
        # Tail scope is strictly enumerated. Full quote is always retained.
        tail_ok = (not tail.strip() or TEMPORAL_TAIL.fullmatch(tail)
                   or re.fullmatch(r"(?: for \$\d+(?:\.\d+)?(?: million| billion)?)?(?: in \d{4})?"
                                   r"(?:,? but the (?:deal|transaction) was cancel(?:led|ed))?", tail))
        if not tail_ok:
            continue
        modal = "alleged" if m["modal"] == "allegedly " else "possible" if m["modal"] else "asserted"
        if re.search(r"\b(?:proposed|planned|attempted|failed)\b", phrase) or scope(phrase,evidence)["lifecycle"] == "cancelled":
            modal = "possible"  # Never a completed-acquisition assertion.
        binaries.append(Candidate(subject=m["s"].strip('"'), predicate=phrase,
            object=m["o"].strip('"'), evidence=evidence, modality=modal,
            polarity="negative" if m["neg"] or m["modalneg"] else "positive", **dates))
    return binaries[:60], events[:12]
