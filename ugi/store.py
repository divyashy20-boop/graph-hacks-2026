from __future__ import annotations

import json
import re
from contextlib import contextmanager
from threading import RLock, local

from redis import Redis
from redis.exceptions import ResponseError

from .models import Settings, uid

KINDS = {
    "Source", "Chunk", "Entity", "Claim", "Evidence", "Mention", "MergeDecision",
    "Hypothesis", "Investigation", "ReviewTask", "AgentAction", "Usage", "RelationEvent",
}


def literal(value):
    if isinstance(value, dict):
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) for k in value):
            raise ValueError("Invalid parameter")
        return "{" + ",".join(k + ":" + literal(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(literal(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


class Store:
    """Single graph per authenticated owner and dataset; atomic document/action commits."""

    def __init__(self, settings: Settings, owner="local", dataset="demo", client=None):
        self.settings = settings
        self.graph = settings.graph_prefix + "_" + uid(owner, dataset)[:24]
        self.owner = owner
        self.client = client
        self.records = {}
        self.links = set()
        self.lock = RLock()
        self._transaction_state = local()
        if settings.backend == "falkordb":
            self.client = client or Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=3,
                socket_timeout=15,
            )
            for label, fields in [("Record", "id"), ("Record", "kind"),
                                  ("Entity", "name_key"), ("Entity", "identity_key"),
                                  ("Claim", "subject_id"), ("Claim", "object_id")]:
                try:
                    self.query(f"CREATE INDEX FOR (n:{label}) ON (n.{fields})")
                except ResponseError as exc:
                    if "already indexed" not in str(exc):
                        raise

    def query(self, text, params=None):
        prefix = "CYPHER " + " ".join(k + "=" + literal(v) for k, v in (params or {}).items())
        command = (prefix + " " if params else "") + text
        result = self.client.execute_command("GRAPH.QUERY", self.graph, command, "TIMEOUT", 5000)
        return result[1] if len(result) > 2 else []

    def ping(self):
        return self.settings.backend == "memory" or self.query("RETURN 1") == [[1]]

    @contextmanager
    def transaction(self):
        if self.client:
            if getattr(self._transaction_state, "depth", 0):
                yield
                return
            # One worker per dataset; leases exceed the bounded invocation budget.
            with self.client.lock(self.graph + ":write", timeout=240, blocking_timeout=3):
                self._transaction_state.depth = 1
                try:
                    yield
                finally:
                    self._transaction_state.depth = 0
        else:
            with self.lock:
                yield

    def get(self, record_id):
        if not self.client:
            return self.records.get(record_id)
        rows = self.query("MATCH (n:Record {id:$id}) RETURN n.payload LIMIT 1", {"id": record_id})
        return json.loads(rows[0][0]) if rows else None

    def list(self, kind, limit=2000):
        if kind not in KINDS or not 1 <= limit <= 20000:
            raise ValueError("Invalid retrieval limit or record kind")
        if not self.client:
            return [r for r in self.records.values() if r["kind"] == kind][:limit]
        rows = self.query(f"MATCH (n:{kind}) RETURN n.payload ORDER BY n.id LIMIT {limit}")
        return [json.loads(row[0]) for row in rows]

    def entities(self, name):
        from .models import key

        direct = self.get(name)
        if direct and direct["kind"] == "Entity":
            return [direct]
        if not self.client:
            return [e for e in self.list("Entity", 5000)
                    if key(name) in [e["name_key"], *e.get("alias_keys", [])]]
        rows = self.query(
            "MATCH (e:Entity) WHERE e.name_key=$key OR $key IN e.alias_keys "
            "RETURN e.payload LIMIT 21", {"key": key(name)},
        )
        return [json.loads(row[0]) for row in rows]

    def claims(self, subject=None, object_id=None):
        if not self.client:
            return [c for c in self.list("Claim", 20000)
                    if (subject is None or c["subject_id"] == subject)
                    and (object_id is None or c["object_id"] == object_id)]
        conditions, params = [], {}
        for field, value in [("subject_id", subject), ("object_id", object_id)]:
            if value is not None:
                conditions.append(f"c.{field}=${field}")
                params[field] = value
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self.query("MATCH (c:Claim)" + where + " RETURN c.payload LIMIT 20001", params)
        if len(rows) > 20000:
            raise ValueError("Claim retrieval budget exceeded")
        return [json.loads(row[0]) for row in rows]

    def neighbors(self, entity_id, reverse=False, limit=200):
        if not self.client:
            matches = self.claims(object_id=entity_id) if reverse else self.claims(entity_id)
            if len(matches) > limit:
                raise ValueError("Neighbour budget exceeded")
            return matches
        pattern = "(other:Entity)-[r:RELATES]->(e:Entity {id:$id})" if reverse else (
            "(e:Entity {id:$id})-[r:RELATES]->(other:Entity)"
        )
        rows = self.query(
            "MATCH " + pattern + " WITH r.claim_id AS cid MATCH (c:Claim) WHERE c.id=cid "
            f"RETURN c.payload LIMIT {limit + 1}", {"id": entity_id},
        )
        if len(rows) > limit:
            raise ValueError("Neighbour budget exceeded")
        return [json.loads(row[0]) for row in rows]

    def counts(self):
        if not self.client:
            return {kind: sum(r["kind"] == kind for r in self.records.values()) for kind in KINDS}
        return dict(self.query("MATCH (n:Record) RETURN n.kind,count(n)"))

    def events(self, entity_id=None, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError("Event limit must be between 1 and 500")
        if entity_id is None:
            return self.list("RelationEvent", limit)
        if not self.client:
            return [e for e in self.list("RelationEvent", 20000)
                    if any(p["entity_id"] == entity_id for p in e["participants"])][:limit]
        rows = self.query(
            "MATCH (e:RelationEvent)-[:HAS_PARTICIPANT]->(:Entity {id:$id}) "
            f"RETURN DISTINCT e.payload ORDER BY e.id LIMIT {limit}", {"id": entity_id},
        )
        return [json.loads(row[0]) for row in rows]

    def commit(self, records, links=()):
        records = list({r["id"]: r for r in records}.values())
        links = list(links)
        if any(r["kind"] not in KINDS for r in records):
            raise ValueError("Unknown record kind")
        if not self.client:
            self.records.update({r["id"]: r for r in records})
            self.links.update(tuple(link) for link in links)
            return
        if not records and not links:
            return
        # Classification and the ONE mutating query share the existing dataset
        # lease. Nested Engine/provider commits reuse the same thread's lease.
        with self.transaction():
            ids = {r["id"] for r in records} | {n for link in links for n in link[:2]}
            existing = {row[0] for row in self.query(
                "UNWIND $ids AS wanted MATCH (n:Record {id:wanted}) RETURN n.id",
                {"ids": sorted(ids)})}
            if ids - existing - {r["id"] for r in records}:
                raise ValueError("Graph link endpoint missing; document not written")
            self._write_classified(records, links, existing)

    def _write_classified(self, records, links, existing):
        if existing:
            # This server build mishandles mixed pending/persisted node pools.
            # Keep its proven MERGE path for updates/shared identities rather
            # than risk reassigning evidence or roles for a throughput claim.
            self.last_write_strategy = "legacy_existing_endpoints"
            return self._write_legacy(records, links)
        self.last_write_strategy = "bound_nodes_all_new"
        params, clauses = {}, []
        values = [dict(id=r["id"], payload=json.dumps(r, ensure_ascii=False),
                       kind=r["kind"], name_key=r.get("name_key", ""),
                       alias_keys=r.get("alias_keys", []), identity_key=r.get("identity_key", ""),
                       subject_id=r.get("subject_id", ""), object_id=r.get("object_id", ""))
                  for r in records]
        params["new"] = values
        clauses.append("UNWIND $new AS value_new CREATE (created:Record) SET created += value_new "
                       "WITH collect(created) AS pool_new")
        # Keep actual node references: resolving each endpoint with MERGE scans
        # all pending nodes in this FalkorDB build, producing quadratic work.
        # The sorted pool has a deterministic ordinal for each unique stable ID.
        clauses.append("UNWIND pool_new AS bound WITH bound ORDER BY bound.id "
                       "WITH collect(bound) AS nodes")
        ordinals = {ident: i for i, ident in enumerate(sorted(
            {r["id"] for r in records}))}
        for kind in sorted({r["kind"] for r in records}):
            clauses.append(f"FOREACH(typed_{kind} IN [n IN nodes WHERE n.kind='{kind}'] | "
                           f"SET typed_{kind}:{kind})")
        for rel in sorted({link[2] for link in links}):
            if rel not in {"RELATES", "HAS_CHUNK", "SUPPORTS", "CITES", "HAS_TASK", "ACTED_ON",
                           "HAS_PARTICIPANT"}:
                raise ValueError("Unknown edge kind")
            params[rel] = [dict(ai=ordinals[link[0]], bi=ordinals[link[1]], claim_id=link[3],
                                role=link[4] if len(link) == 5 else "")
                           for link in links if link[2] == rel]
            row, a, b, edge = "row_"+rel, "source_"+rel, "target_"+rel, "edge_"+rel
            clauses.append(f"FOREACH({row} IN ${rel} | "
                           f"FOREACH({a} IN [nodes[{row}.ai]] | "
                           f"FOREACH({b} IN [nodes[{row}.bi]] | "
                           f"MERGE ({a})-[{edge}:{rel} {{claim_id:{row}.claim_id}}]->({b}) "
                           f"SET {edge}.role={row}.role)))")
        if clauses:
            # One GRAPH.QUERY remains the atomic document/action write. No
            # partial batch commits and no timeout change.
            self.query(" ".join(clauses), params)

    def _write_legacy(self, records, links):
        """Known-good C atomic write, retained for mixed/update documents."""
        params, clauses = {}, []
        for kind in sorted({r["kind"] for r in records}):
            params[kind] = [dict(id=r["id"], payload=json.dumps(r, ensure_ascii=False),
                                kind=kind, name_key=r.get("name_key", ""),
                                alias_keys=r.get("alias_keys", []), identity_key=r.get("identity_key", ""),
                                subject_id=r.get("subject_id", ""), object_id=r.get("object_id", ""))
                            for r in records if r["kind"] == kind]
            clauses.append(f"FOREACH(v IN ${kind} | MERGE (n:Record:{kind} {{id:v.id}}) SET n += v)")
        for rel in sorted({link[2] for link in links}):
            if rel not in {"RELATES", "HAS_CHUNK", "SUPPORTS", "CITES", "HAS_TASK", "ACTED_ON",
                           "HAS_PARTICIPANT"}:
                raise ValueError("Unknown edge kind")
            params[rel] = [dict(a=link[0], b=link[1], claim_id=link[3],
                                role=link[4] if len(link) == 5 else "")
                           for link in links if link[2] == rel]
            clauses.append(f"FOREACH(v IN ${rel} | MERGE (a:Record {{id:v.a}}) "
                           "MERGE (b:Record {id:v.b}) "
                           f"MERGE (a)-[r:{rel} {{claim_id:v.claim_id}}]->(b) SET r.role=v.role)")
        self.query(" ".join(clauses), params)

    def consume(self, bucket, limit, amount=1):
        """Durable Redis counters are shared across datasets; failed attempts stay charged."""
        if self.client:
            code = ("local n=tonumber(redis.call('GET',KEYS[1]) or '0'); "
                    "if n+tonumber(ARGV[1])>tonumber(ARGV[2]) then return 0 end; "
                    "redis.call('INCRBY',KEYS[1],ARGV[1]); "
                    "redis.call('EXPIRE',KEYS[1],172800); return 1")
            if not self.client.eval(code, 1, self.settings.graph_prefix + ":quota:" + bucket,
                                    amount, limit):
                raise ValueError("Quota exceeded")
        else:
            with self.lock:
                quota_id = "quota:" + bucket
                used = self.records.get(quota_id, {}).get("used", 0)
                if used + amount > limit:
                    raise ValueError("Quota exceeded")
                self.records[quota_id] = {"id": quota_id, "kind": "Usage", "used": used + amount}
