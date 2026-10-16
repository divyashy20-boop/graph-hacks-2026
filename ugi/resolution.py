"""Source-grounded, operator-authority evidence and bounded identity blocking.

No model, uploaded 'trusted' flag, name equality or raw external_id can approve
identity. Policy-approved authority evidence is still not an external registry check.
"""
from __future__ import annotations

import re
from time import perf_counter

from pydantic import Field, model_validator

from .identity import IdentityLedger, RecordID
from .models import Strict, key, now, uid

VERSION = "identity-resolution-v1"
POSTING_QUERY = ("MATCH (p:IdentityPosting) WHERE p.block_key IN $keys "
                 "RETURN DISTINCT p.snapshot_id LIMIT $limit")


def normalized_name(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


class Identifier(Strict):
    namespace: str = Field(pattern=r"^[a-zA-Z0-9_:-]{1,80}$")
    value: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def opaque_identifier(self):
        if not self.value.strip() or self.value != self.value.strip():
            raise ValueError("Identifier must be nonblank with no surrounding whitespace")
        return self


class AuthorityObservation(Strict):
    mention_snapshot_id: RecordID
    authority: str = Field(min_length=1, max_length=80)
    identifiers: list[Identifier] = Field(min_length=1, max_length=8)
    idempotency_key: str = Field(min_length=1, max_length=100)
    authorise_action: bool = False


class IdentityResolver:
    def __init__(self, store):
        self.store = store
        self.ledger = IdentityLedger(store)

    def get(self, ident, pending):
        if ident not in pending:
            pending[ident] = self.store.get(ident)
        return pending[ident]

    def snapshot(self, mid, pending):
        record = self.get(mid, pending)
        if not record or record["kind"] != "MentionSnapshot":
            raise ValueError("Missing MentionSnapshot in this dataset")
        return record

    def evidence(self, mid, pending):
        head = self.get(uid(VERSION, "evidence_head", mid), pending)
        records = [self.get(eid, pending) for eid in head["evidence_ids"]] if head else []
        trusted = {}
        for record in records:
            allowed = self.store.settings.identity_authorities.get(record["authority"], [])
            for ident in record["identifiers"]:
                if ident["namespace"] in allowed:
                    trusted.setdefault(ident["namespace"], set()).add(ident["value"])
        return trusted, records

    def blocks(self, mid, pending):
        snapshot = self.snapshot(mid, pending)
        profile = self.get(uid(VERSION, "profile", mid), pending)
        names = profile["names"] if profile else [normalized_name(snapshot["text"])]
        trusted, _ = self.evidence(mid, pending)
        return ([uid("name", key(snapshot["entity_type"]), n) for n in names if n]
                + [uid("identifier", key(snapshot["entity_type"]), ns, value)
                   for ns, values in trusted.items() for value in values])

    def candidates(self, mid, pending=None):
        pending = pending or {}
        started = perf_counter()
        keys = self.blocks(mid, pending)
        limit = self.store.settings.identity_candidate_limit
        if self.store.client:
            rows = self.store.query(POSTING_QUERY, {"keys": keys, "limit": limit+2})
            found = {r[0] for r in rows}
        else:
            found = {r["snapshot_id"] for r in self.store.list("IdentityPosting", 20000)
                     if r["block_key"] in keys}
        found.update(r["snapshot_id"] for r in pending.values()
                     if r and r["kind"] == "IdentityPosting" and r["block_key"] in keys)
        found.discard(mid)
        selected = sorted(found)[:limit]
        profile = self.get(uid(VERSION, "profile", mid), pending)
        limited = bool(profile and profile.get("aliases_truncated"))
        return dict(mention_snapshot_id=mid, candidate_ids=selected, complete=len(found) <= limit and not limited,
                    aliases_truncated=limited,
                    block_count=len(keys), candidate_count=len(selected),
                    elapsed_ms=round((perf_counter()-started)*1000, 3),
                    semantics="Bounded candidate retrieval, not proof of identity")

    def compare(self, left, right, pending=None, reuse=True):
        pending = pending or {}
        a, b = self.snapshot(left, pending), self.snapshot(right, pending)
        av, ae = self.evidence(left, pending)
        bv, be = self.evidence(right, pending)
        conflict = sorted(ns for ns in av.keys() & bv.keys() if av[ns] != bv[ns])
        ambiguous = any(len(values) != 1 for values in [*av.values(), *bv.values()])
        shared = sorted(ns for ns in av.keys() & bv.keys() if av[ns] == bv[ns] and len(av[ns]) == 1)
        names_equal = normalized_name(a["text"]) == normalized_name(b["text"])
        if key(a["entity_type"]) != key(b["entity_type"]):
            decision, reason = "DIFFERENT_ENTITY", "Incompatible declared entity types"
        elif ambiguous:
            decision, reason = "UNRESOLVED", "An authority observation has conflicting identifiers"
        elif conflict:
            decision, reason = "DIFFERENT_ENTITY", "Conflicting policy-trusted exclusive namespace identifiers"
        elif shared:
            decision, reason = "SAME_ENTITY", "Same policy-trusted typed exclusive identifier; no negative constraint"
        elif names_equal:
            decision, reason = "POSSIBLY_SAME", "Name equality alone cannot establish identity"
        else:
            decision, reason = "UNRESOLVED", "No sufficient reliable identity evidence"
        signature = uid(VERSION, sorted([left, right]), sorted(r["id"] for r in ae+be),
                        self.store.settings.identity_authorities)
        old = self.get(signature, pending) if reuse else None
        return old or dict(id=signature, kind="IdentityAssessment", algorithm=VERSION,
            left_id=left, right_id=right, decision=decision, reason=reason, recorded_at=now(),
            evidence_ids=sorted({r["id"] for r in ae+be}),
            features=dict(names_equal=names_equal, shared_namespaces=shared,
                          conflicting_namespaces=conflict, internally_ambiguous=ambiguous),
            calibrated=False, eligible_for_inference=False, policy_hash=uid(self.store.settings.identity_authorities))

    def postings(self, mid, pending):
        return [dict(id=uid(VERSION, "posting", block, mid), kind="IdentityPosting",
                     block_key=block, snapshot_id=mid) for block in self.blocks(mid, pending)]

    def stage(self, records):
        pending = {r["id"]: r for r in records}
        output = []
        entities = {r["id"]: r for r in records if r["kind"] == "Entity"}
        mids = [r["id"] for r in records if r["kind"] == "MentionSnapshot"]
        for mid in mids:
            snapshot = pending[mid]
            entity = entities[snapshot["entity_id"]]
            aliases = sorted(set(entity.get("aliases", [])))
            profile = dict(id=uid(VERSION, "profile", mid), kind="IdentityProfile", snapshot_id=mid,
                           aliases_truncated=len(aliases) > 20,
                           names=sorted({normalized_name(n) for n in
                                         [snapshot["text"], *aliases[:20]] if n.strip()}))
            output.append(profile)
            pending[profile["id"]] = profile
            for posting in self.postings(mid, pending):
                output.append(posting)
                pending[posting["id"]] = posting
        for mid in mids:
            for candidate in self.candidates(mid, pending)["candidate_ids"]:
                decision = self.compare(mid, candidate, pending)
                if not self.get(decision["id"], pending):
                    output.append(decision)
                    pending[decision["id"]] = decision
        return output

    def observe(self, request: AuthorityObservation, actor):
        if not request.authorise_action or self.store.settings.identity_resolution == "off":
            raise ValueError("Authority evidence requires explicit authorization and identity resolution opt-in")
        allowed = self.store.settings.identity_authorities.get(request.authority, [])
        if not allowed or any(i.namespace not in allowed for i in request.identifiers):
            raise ValueError("Authority/namespace not approved by operator policy")
        with self.store.transaction():
            ident = uid(VERSION, "evidence", request.idempotency_key)
            request_hash = uid(request.model_dump(), actor)
            old = self.ledger._replay(ident, request_hash, "IdentityEvidence")
            if old:
                return old
            snapshot = self.snapshot(request.mention_snapshot_id, {})
            chunk = self.ledger.required(snapshot["chunk_id"], "Chunk")
            entries = (chunk.get("record") or {}).get("identity", [])
            if not isinstance(entries, list) or len(entries) > 100:
                raise ValueError("Invalid bounded structured identity evidence list")
            for item in request.identifiers:
                if not any(isinstance(entry, dict) and entry.get("name") == snapshot["text"]
                           and entry.get("entity_type") == snapshot["entity_type"]
                           and entry.get("namespace") == item.namespace and entry.get("value") == item.value
                           for entry in entries):
                    raise ValueError("Identifier lacks an exact structured source mapping")
            evidence = dict(id=ident, kind="IdentityEvidence", request_hash=request_hash,
                            snapshot_id=snapshot["id"], source_id=snapshot["source_id"],
                            authority=request.authority, identifiers=[i.model_dump() for i in request.identifiers],
                            actor=actor, recorded_at=now(), algorithm=VERSION,
                            trust_basis="Operator-authorized source origin; no external registry validation")
            head_id = uid(VERSION, "evidence_head", snapshot["id"])
            head = self.store.get(head_id)
            previous = [self.store.get(eid) for eid in head["evidence_ids"]] if head else []
            active = [r["id"] for r in previous if r["authority"] != request.authority] + [ident]
            if len(active) > 8:
                raise ValueError("Authority evidence history head budget exceeded")
            new_head = dict(id=head_id, kind="IdentityEvidenceHead", evidence_ids=active)
            pending = {ident: evidence, head_id: new_head}
            postings = self.postings(snapshot["id"], pending)
            pending.update({p["id"]: p for p in postings})
            decisions = [self.compare(snapshot["id"], cid, pending)
                         for cid in self.candidates(snapshot["id"], pending)["candidate_ids"]]
            from .identity_policy import IdentityPolicy

            planned, run = IdentityPolicy(self.store).plan(snapshot["id"], pending)
            evidence["automation_run_id"] = run["id"]
            self.ledger._commit_bounded([evidence, new_head, *postings, *decisions, *planned, run])
            return evidence
