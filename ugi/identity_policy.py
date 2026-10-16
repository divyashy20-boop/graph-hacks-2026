"""Bounded cluster-level negative constraints; opt-in reversible overlay only."""
from itertools import combinations

from .identity import IdentityLedger
from .models import now, uid
from .resolution import VERSION, IdentityResolver

CLUSTER_LIMIT = 50
CLUSTER_QUERY = ("MATCH (h:IdentityAssignment) WHERE h.cluster_id=$cluster "
                 "RETURN h.payload LIMIT 51")


class IdentityPolicy:
    def __init__(self, store):
        self.store = store
        self.ledger, self.resolver = IdentityLedger(store), IdentityResolver(store)

    def members(self, mid):
        assignment = self.ledger.assignment(mid)
        cluster = assignment["cluster_id"]
        manifest = self.store.get(uid("identity-cluster-manifest", cluster))
        if not manifest or len(manifest["member_universe"]) > CLUSTER_LIMIT:
            return dict(complete=False, cluster_id=cluster, member_ids=[], reason="Legacy/unbounded cluster lacks complete manifest")
        if self.store.client:
            import json

            heads = [json.loads(r[0]) for r in self.store.query(CLUSTER_QUERY, {"cluster": cluster})]
        else:
            heads = [r for r in self.store.list("IdentityAssignment", 20000) if r.get("cluster_id") == cluster]
        found = {h["mention_snapshot_id"] for h in heads}
        expected = {m for m in manifest["member_universe"] if self.ledger.assignment(m)["cluster_id"] == cluster}
        complete = len(heads) <= CLUSTER_LIMIT and found == expected and mid in found
        return dict(complete=complete, cluster_id=cluster, member_ids=sorted(found) if complete else [],
                    reason="Indexed heads checked against immutable membership universe")

    def cached(self, mids, pending):
        cached = dict(pending)
        for mid in mids:
            for ident in (mid, uid(VERSION, "evidence_head", mid)):
                record = self.resolver.get(ident, cached)
                cached[ident] = record  # Cache misses too: no repeated DB reads per pair.
            head = cached.get(uid(VERSION, "evidence_head", mid))
            for eid in head["evidence_ids"] if head else []:
                cached[eid] = self.resolver.get(eid, cached)
        return cached

    def analyze(self, mids, pending=None):
        if len(mids) > CLUSTER_LIMIT:
            return dict(state="INCOMPLETE", groups=None, conflicts=[], evidence_ids=[], pair_checks=0)
        pending = self.cached(mids, pending or {})
        evidence_ids, internally_ambiguous = set(), []
        for mid in mids:
            trusted, records = self.resolver.evidence(mid, pending)
            evidence_ids.update(r["id"] for r in records)
            if any(len(values) != 1 for values in trusted.values()):
                internally_ambiguous.append(mid)
        pairs = {(a, b): self.resolver.compare(a, b, pending, reuse=False)
                 for a, b in combinations(sorted(mids), 2)}
        conflicts = [dict(left=a, right=b, reason=d["reason"], features=d["features"])
                     for (a, b), d in pairs.items() if d["decision"] == "DIFFERENT_ENTITY"]
        # SAME edges are only a proposal to group. A negative within their
        # transitive component vetoes it; unknown within/cross groups also vetoes.
        groups = [{m} for m in sorted(mids)]
        for (a, b), decision in pairs.items():
            if decision["decision"] == "SAME_ENTITY":
                ga = next(g for g in groups if a in g)
                gb = next(g for g in groups if b in g)
                if ga is not gb:
                    ga.update(gb)
                    groups.remove(gb)
        safe = not internally_ambiguous
        for (a, b), decision in pairs.items():
            together = any(a in g and b in g for g in groups)
            safe &= decision["decision"] == ("SAME_ENTITY" if together else "DIFFERENT_ENTITY")
            if not together:
                # Declared type differences may expose inconsistency, but are
                # not enough to autonomously split on untrusted source typing.
                safe &= bool(decision["features"]["conflicting_namespaces"])
        state = "INCONSISTENT" if conflicts or internally_ambiguous else (
            "CONSISTENT" if len(groups) == 1 and safe else "UNRESOLVED")
        return dict(state=state, conflicts=conflicts, internally_ambiguous=internally_ambiguous,
                    groups=sorted(sorted(g) for g in groups) if safe else None,
                    evidence_ids=sorted(evidence_ids), pair_checks=len(pairs),
                    eligible_for_inference=False, calibrated=False)

    def inspect(self, mid, pending=None):
        with self.store.transaction():
            membership = self.members(mid)
            return dict(membership=membership, analysis=self.analyze(membership["member_ids"], pending)
                        if membership["complete"] else dict(state="INCOMPLETE", groups=None))

    def plan(self, mid, pending):
        """Called under observation lease; returns records, never commits halfway."""
        inspected = self.inspect(mid, pending)
        analysis = inspected["analysis"]
        proposal, reason = None, "No defensible automatic identity revision"
        retrieval = self.resolver.candidates(mid, pending)
        if analysis["state"] == "INCONSISTENT":
            if analysis["groups"] and len(analysis["groups"]) > 1:
                proposal, reason = analysis["groups"], "Whole-cluster exclusive identifier/type conflicts; complete disjoint partition"
        elif inspected["membership"]["complete"] and retrieval["complete"]:
            members = set(inspected["membership"]["member_ids"])
            clusters_complete = True
            for candidate in retrieval["candidate_ids"]:
                if self.resolver.compare(mid, candidate, pending)["decision"] == "SAME_ENTITY":
                    cluster = self.members(candidate)
                    clusters_complete &= cluster["complete"]
                    members.update(cluster["member_ids"])
            combined = self.analyze(sorted(members), pending)
            if (clusters_complete and combined["state"] == "CONSISTENT" and combined["groups"]
                    and len(members) > len(inspected["membership"]["member_ids"])):
                proposal = combined["groups"]
                analysis = combined
                reason = "Every pair across complete clusters has compatible policy-trusted identity evidence"
        run = dict(id=uid("identity-run-v1", mid, sorted(pending), inspected,
                          self.store.settings.identity_auto_apply, self.store.settings.identity_authorities),
                   kind="IdentityRun", algorithm="identity-cluster-policy-v1", recorded_at=now(),
                   snapshot_id=mid, inspected=inspected, proposed_groups=proposal, reason=reason,
                   candidate_complete=retrieval["complete"], pair_checks=analysis.get("pair_checks", 0),
                   applied_revision_id=None, mode="apply" if self.store.settings.identity_auto_apply else "dry_run",
                   eligible_for_inference=False)
        records = []
        if proposal and self.store.settings.identity_auto_apply:
            records, revision = self.ledger.plan_projection(proposal, analysis["evidence_ids"],
                uid(self.store.settings.identity_authorities), reason)
            run["applied_revision_id"] = revision["id"]
        return records, run
