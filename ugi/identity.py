"""Bounded immutable observation ledger; provisional identities never rewire facts."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import Strict, now, uid

VERSION = "identity-ledger-v1"
MAX_MENTIONS = 200
MAX_HISTORY = 200
MAX_DEPENDENTS = 200
RecordID = Annotated[str, Field(min_length=1, max_length=160)]
DEPENDENCY_QUERY = (
    "MATCH (m:Record) WHERE m.id IN $ids AND m.kind='MentionSnapshot' "
    "WITH m MATCH (a:DerivedArtifact)-[:USES_IDENTITY]->(m) "
    "RETURN DISTINCT a.id LIMIT 201"
)


class IdentityChange(Strict):
    operation: Literal["provisional_merge", "split", "revert"]
    mention_snapshot_ids: list[RecordID] = Field(default_factory=list, max_length=100)
    revision_id: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=1, max_length=100)
    authorise_action: bool = False

    @model_validator(mode="after")
    def shape(self):
        if self.operation == "revert":
            if not self.revision_id or self.mention_snapshot_ids:
                raise ValueError("Revert requires revision_id only")
        elif (self.revision_id or not self.mention_snapshot_ids
              or len(set(self.mention_snapshot_ids)) != len(self.mention_snapshot_ids)):
            raise ValueError("Unique mention_snapshot_ids required")
        if self.operation == "provisional_merge" and len(self.mention_snapshot_ids) < 2:
            raise ValueError("A provisional merge requires at least two mentions")
        return self


class ArtifactRequest(Strict):
    mention_snapshot_ids: list[RecordID] = Field(min_length=1, max_length=100)
    output: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=100)
    authorise_action: bool = False


class IdentityLedger:
    def __init__(self, store):
        self.store = store

    def required(self, ident, kind):
        value = self.store.get(ident)
        if not value or value["kind"] != kind:
            raise ValueError("Missing " + kind + " in this dataset")
        return value

    def stage(self, records):
        """Called under ingestion's lease, before its SINGLE atomic commit."""
        mentions = [r for r in records if r["kind"] == "Mention"]
        if len(mentions) > MAX_MENTIONS:
            raise ValueError("Identity ledger mention budget exceeded (200 per upload)")
        entities = {r["id"]: r for r in records if r["kind"] == "Entity"}
        dependents = {uid(r["id"], side): r["id"] for r in records if r["kind"] == "Claim"
                      for side in ("subject", "object")}
        grouped = defaultdict(list)
        stamp = now()
        for mention in mentions:
            entity = entities[mention["entity_id"]]
            grouped[entity["id"]].append(dict(
                id=uid(VERSION, "snapshot", mention["id"]), kind="MentionSnapshot",
                mention_id=mention["id"], entity_id=entity["id"], text=mention["text"],
                entity_type=entity["entity_type"], external_id=entity.get("external_id"),
                source_id=mention["source_id"], chunk_id=mention["chunk_id"],
                dependent_record_id=mention.get("event_id") or dependents[mention["id"]],
                role=mention.get("role"), location=mention["location"], recorded_at=stamp,
                identity_basis="source_supplied_typed_id" if entity.get("external_id")
                else "document_local_not_cross_document_identity", calibrated=False,
            ))
        output = []
        for eid, observations in grouped.items():
            head_id = uid(VERSION, "card_head", eid)
            previous = self.store.get(head_id)
            observed_count = (previous.get("mention_count", 0) if previous else 0) + len(observations)
            if observed_count > MAX_MENTIONS or (previous and previous["version"] >= MAX_HISTORY):
                raise ValueError("Entity card history/mention budget exceeded")
            card = dict(id=uid(VERSION, "card", eid, observations[0]["source_id"]),
                        kind="EntityCard", entity_id=eid, algorithm=VERSION,
                        version=previous["version"]+1 if previous else 1,
                        previous_id=previous["card_id"] if previous else None,
                        mention_snapshot_ids=[m["id"] for m in observations], recorded_at=stamp)
            revision = dict(id=uid(card["id"], "assignment"), kind="IdentityRevision",
                            operation="initial_assignment", algorithm=VERSION, recorded_at=stamp,
                            actor="automatic_source_identity_policy", status="source_anchor_only",
                            eligible_for_inference=False, calibrated=False,
                            reason="Typed supplied ID or document-local anchor; name alone never unions documents",
                            affected_record_ids=sorted({m["dependent_record_id"] for m in observations}),
                            changes=[dict(mention_snapshot_id=m["id"], previous_revision_id=None,
                                          old_cluster_id=None, new_cluster_id=(uid("identity-unresolved", m["id"])
                                          if self.store.settings.identity_resolution != "off" else eid))
                                     for m in observations])
            output.extend([*observations, card, revision,
                           dict(id=head_id, kind="EntityCardHead", entity_id=eid,
                                card_id=card["id"], version=card["version"], mention_count=observed_count)])
            output.extend(dict(id=uid(VERSION, "assignment", m["id"]), kind="IdentityAssignment",
                               mention_snapshot_id=m["id"], revision_id=revision["id"], version=1)
                          for m in observations)
            for head in output:
                if head["kind"] == "IdentityAssignment" and "cluster_id" not in head:
                    head["cluster_id"] = next(c["new_cluster_id"] for c in revision["changes"]
                                              if c["mention_snapshot_id"] == head["mention_snapshot_id"])
            if self.store.settings.identity_resolution != "off":
                output.extend(self.cluster_manifest(c["new_cluster_id"], [c["mention_snapshot_id"]])
                              for c in revision["changes"])
        return output

    def assignment(self, snapshot_id, as_known_at=None):
        with self.store.transaction():
            return self._assignment(snapshot_id, as_known_at)

    def _assignment(self, snapshot_id, as_known_at=None):
        snapshot = self.required(snapshot_id, "MentionSnapshot")
        head = self.required(uid(VERSION, "assignment", snapshot_id), "IdentityAssignment")
        point = datetime.fromisoformat(as_known_at) if as_known_at else None
        if point and point.tzinfo is None:
            raise ValueError("as_known_at requires an explicit timezone")
        revision_id = head["revision_id"]
        for _ in range(MAX_HISTORY):
            revision = self.required(revision_id, "IdentityRevision")
            change = next(c for c in revision["changes"] if c["mention_snapshot_id"] == snapshot_id)
            if point is None or datetime.fromisoformat(revision["recorded_at"]) <= point:
                return dict(mention=snapshot, revision_id=revision_id,
                            cluster_id=change["new_cluster_id"], status=revision["status"],
                            eligible_for_inference=False, calibrated=False)
            revision_id = change["previous_revision_id"]
            if revision_id is None:
                return None
        raise ValueError("Identity revision history budget exceeded")

    def card(self, entity_id, as_known_at=None):
        with self.store.transaction():
            return self._card(entity_id, as_known_at)

    def _card(self, entity_id, as_known_at=None):
        head = self.required(uid(VERSION, "card_head", entity_id), "EntityCardHead")
        point = datetime.fromisoformat(as_known_at) if as_known_at else None
        if point and point.tzinfo is None:
            raise ValueError("as_known_at requires an explicit timezone")
        card_id, versions, mentions = head["card_id"], [], []
        for _ in range(MAX_HISTORY):
            card = self.required(card_id, "EntityCard")
            if point is None or datetime.fromisoformat(card["recorded_at"]) <= point:
                versions.append(card)
                for mid in card["mention_snapshot_ids"]:
                    if len(mentions) >= MAX_MENTIONS:
                        raise ValueError("Card projection mention budget exceeded")
                    assignment = self.assignment(mid, as_known_at)
                    if assignment:
                        mentions.append(assignment)
            card_id = card["previous_id"]
            if card_id is None:
                return dict(entity_id=entity_id, versions=versions, mentions=mentions,
                            as_known_at=as_known_at, eligible_for_inference=False,
                            semantics="Source-backed observations and provisional identity projection; not identity truth")
        raise ValueError("Card version history budget exceeded")

    def _replay(self, ident, request_hash, kind):
        old = self.store.get(ident)
        if old:
            if old["kind"] != kind or old["request_hash"] != request_hash:
                raise ValueError("Idempotency key reused with different request")
            return old
        return None

    def _dependent_artifacts(self, snapshot_ids):
        if self.store.client:
            rows = self.store.query(DEPENDENCY_QUERY, {"ids": snapshot_ids})
            result = {row[0] for row in rows}
        else:
            result = {a for a, b, rel, *_ in self.store.links
                      if rel == "USES_IDENTITY" and b in snapshot_ids}
        if len(result) > MAX_DEPENDENTS:
            raise ValueError("Identity dependency fanout budget exceeded")
        return sorted(result)

    def revise(self, request: IdentityChange, actor):
        if not request.authorise_action:
            raise ValueError("Explicit authorise_action required for identity revision")
        with self.store.transaction():
            ident = uid(VERSION, "revision", request.idempotency_key)
            request_hash = uid(request.model_dump(), actor)
            old = self._replay(ident, request_hash, "IdentityRevision")
            if old:
                return old
            reverted = None
            mids = request.mention_snapshot_ids
            if request.operation == "revert":
                reverted = self.required(request.revision_id, "IdentityRevision")
                if reverted["operation"] == "initial_assignment":
                    raise ValueError("Initial source assignments cannot be reverted; use split")
                mids = [c["mention_snapshot_id"] for c in reverted["changes"]]
            current = [self.assignment(mid) for mid in mids]
            if len({c["mention"]["entity_type"] for c in current}) != 1:
                raise ValueError("Cross-type identity merge/split forbidden")
            changes, heads = [], []
            for item in current:
                mid = item["mention"]["id"]
                assignment_id = uid(VERSION, "assignment", mid)
                version = self.required(assignment_id, "IdentityAssignment")["version"] + 1
                if version > MAX_HISTORY:
                    raise ValueError("Identity revision history budget exceeded")
                if reverted:
                    if item["revision_id"] != reverted["id"]:
                        raise ValueError("Cannot revert over a later identity decision")
                    target = next(c["old_cluster_id"] for c in reverted["changes"]
                                  if c["mention_snapshot_id"] == mid)
                else:
                    target = uid(VERSION, "provisional_cluster", ident,
                                 "collective" if request.operation == "provisional_merge" else mid)
                changes.append(dict(mention_snapshot_id=mid, previous_revision_id=item["revision_id"],
                                    old_cluster_id=item["cluster_id"], new_cluster_id=target))
                heads.append(dict(id=assignment_id, kind="IdentityAssignment", version=version,
                                  mention_snapshot_id=mid, revision_id=ident, cluster_id=target))
            artifacts = self._dependent_artifacts(mids)
            revision = dict(id=ident, kind="IdentityRevision", request_hash=request_hash,
                            operation=request.operation, reverts_id=request.revision_id,
                            changes=changes, reason=request.reason, actor=actor, algorithm=VERSION,
                            recorded_at=now(), status="provisional", eligible_for_inference=False,
                            calibrated=False, source_ids=sorted({c["mention"]["source_id"] for c in current}),
                            identifier_conflict=len({c["mention"]["external_id"] for c in current
                                                     if c["mention"].get("external_id")}) > 1,
                            affected_record_ids=sorted({c["mention"]["dependent_record_id"] for c in current}),
                            affected_artifact_ids=artifacts)
            notices = [dict(id=uid(ident, artifact), kind="KnowledgeRevision", revision_id=ident,
                            artifact_id=artifact, state="stale", recorded_at=revision["recorded_at"],
                            reason="An identity assignment used by this artifact changed; re-evaluate")
                       for artifact in artifacts]
            manifests = []
            if not reverted and self.store.settings.identity_resolution != "off":
                for cluster in {c["new_cluster_id"] for c in changes}:
                    manifests.append(self.cluster_manifest(cluster, [c["mention_snapshot_id"] for c in changes
                                                                    if c["new_cluster_id"] == cluster]))
            self._commit_bounded([revision, *heads, *notices, *manifests])
            return revision

    @staticmethod
    def cluster_manifest(cluster, members):
        return dict(id=uid("identity-cluster-manifest", cluster), kind="IdentityCluster",
                    cluster_id=cluster, member_universe=sorted(members), algorithm="cluster-manifest-v1")

    def plan_projection(self, groups, evidence_ids, policy_hash, reason):
        """Internal policy planner. Caller holds lease and commits with evidence atomically."""
        mids = [mid for group in groups for mid in group]
        if not mids or len(mids) > 50 or len(set(mids)) != len(mids) or any(not g for g in groups):
            raise ValueError("Invalid bounded automatic identity partition")
        current = {mid: self.assignment(mid) for mid in mids}
        if any(len({current[m]["mention"]["entity_type"].casefold() for m in group}) != 1 for group in groups):
            raise ValueError("Automatic identity group has incompatible types")
        signature = uid("identity-policy-projection-v1", sorted(sorted(g) for g in groups),
                        sorted((m, a["revision_id"]) for m, a in current.items()),
                        sorted(evidence_ids), policy_hash)
        changes, heads, manifests = [], [], []
        for group in groups:
            target = uid(signature, sorted(group))
            manifests.append(self.cluster_manifest(target, group))
            for mid in group:
                head_id = uid(VERSION, "assignment", mid)
                head = self.required(head_id, "IdentityAssignment")
                if head["revision_id"] != current[mid]["revision_id"] or head["version"] >= MAX_HISTORY:
                    raise ValueError("Identity assignment changed or history budget exceeded")
                changes.append(dict(mention_snapshot_id=mid, previous_revision_id=head["revision_id"],
                                    old_cluster_id=current[mid]["cluster_id"], new_cluster_id=target))
                heads.append(dict(id=head_id, kind="IdentityAssignment", mention_snapshot_id=mid,
                                  revision_id=signature, version=head["version"]+1, cluster_id=target))
        artifacts = self._dependent_artifacts(mids)
        revision = dict(id=signature, kind="IdentityRevision", changes=changes,
                        operation="automatic_partition" if len(groups) > 1 else "automatic_merge",
                        actor="configured_identity_policy", algorithm="identity-policy-projection-v1",
                        reason=reason, recorded_at=now(), status="policy_supported_provisional",
                        calibrated=False, eligible_for_inference=False, evidence_ids=sorted(evidence_ids),
                        policy_hash=policy_hash, affected_artifact_ids=artifacts,
                        affected_record_ids=sorted({a["mention"]["dependent_record_id"] for a in current.values()}))
        notices = [dict(id=uid(signature, aid), kind="KnowledgeRevision", revision_id=signature,
                        artifact_id=aid, state="stale", reason="Consumed identity revision changed; re-evaluate",
                        recorded_at=revision["recorded_at"]) for aid in artifacts]
        return [revision, *heads, *manifests, *notices], revision

    def artifact(self, request: ArtifactRequest):
        if not request.authorise_action:
            raise ValueError("Explicit authorise_action required to persist an artifact")
        with self.store.transaction():
            ident = uid(VERSION, "artifact", request.idempotency_key)
            request_hash = uid(request.model_dump())
            old = self._replay(ident, request_hash, "DerivedArtifact")
            if old:
                return old
            mids = sorted(set(request.mention_snapshot_ids))
            assignments = [self.assignment(mid) for mid in mids]
            record = dict(id=ident, kind="DerivedArtifact", request_hash=request_hash,
                          output=request.output, recorded_at=now(),
                          identity_inputs=[dict(mention_snapshot_id=a["mention"]["id"],
                                                revision_id=a["revision_id"]) for a in assignments],
                          status="unverified_output", eligible_for_inference=False)
            self._commit_bounded([record], [(ident, mid, "USES_IDENTITY", uid(ident, mid)) for mid in mids])
            return record

    def _commit_bounded(self, records, links=()):
        if sum(self.store.counts().values()) + len(records) > 100000:
            raise ValueError("Total record quota exceeded with identity revision")
        self.store.commit(records, links)

    def freshness(self, artifact_id):
        with self.store.transaction():
            return self._freshness(artifact_id)

    def _freshness(self, artifact_id):
        artifact = self.required(artifact_id, "DerivedArtifact")
        # Compare the exact consumed revision: no full-graph notice scan needed.
        changed = [a["mention_snapshot_id"] for a in artifact["identity_inputs"]
                   if self.assignment(a["mention_snapshot_id"])["revision_id"] != a["revision_id"]]
        return dict(artifact=artifact, state="stale" if changed else "current_inputs_only",
                    changed_mention_snapshot_ids=changed, independently_verified=False)
