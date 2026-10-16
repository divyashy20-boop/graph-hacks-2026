"""Declarative vocabularies. Shape validity is not factual or logical validity."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import Strict, now, uid

Token = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,30}$")]
Version = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$")]
TypeRef = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,30}:[A-Z][A-Za-z0-9_]{0,39}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
QUALIFIERS = {"polarity", "modality", "event_time", "valid_from", "valid_to",
              "historical", "attribution", "time_precision", "temporal_source"}


def surface(value):
    return re.sub(r"\s+", " ", value.strip()).casefold()


class PackRef(Strict):
    namespace: Token
    version: Version
    content_hash: Digest


class Role(Strict):
    name: Token
    types: list[TypeRef] = Field(min_length=1, max_length=8)
    minimum: int = Field(default=1, ge=0, le=12)
    maximum: int = Field(default=1, ge=1, le=12)

    @model_validator(mode="after")
    def cardinality(self):
        if self.minimum > self.maximum or len(set(self.types)) != len(self.types):
            raise ValueError("Invalid role cardinality/types")
        return self


class PredicateSpec(Strict):
    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,59}$")
    definition: str = Field(min_length=8, max_length=1000)
    form: Literal["binary", "event"]
    direction: Literal["directed", "collective"] = "directed"
    roles: list[Role] = Field(min_length=2, max_length=12)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    qualifiers: list[str] = Field(default_factory=lambda: sorted(QUALIFIERS), max_length=9)

    @model_validator(mode="after")
    def shape(self):
        names = [r.name for r in self.roles]
        if len(set(names)) != len(names) or not set(self.qualifiers) <= QUALIFIERS:
            raise ValueError("Duplicate roles or unknown qualifiers")
        if self.form == "binary" and (len(names) != 2 or any(r.minimum != 1 or r.maximum != 1 for r in self.roles)):
            raise ValueError("Binary predicates need two ordered singleton roles")
        if self.form == "event" and sum(r.maximum for r in self.roles) < 3:
            raise ValueError("Event needs capacity for at least three participants")
        if self.form == "binary" and self.direction != "directed":
            raise ValueError("Collective relations require whole events")
        for alias in self.aliases:
            if not re.fullmatch(r"[A-Za-z][A-Za-z _-]{0,79}", alias):
                raise ValueError("Aliases must be bounded literal phrases, not executable patterns")
        return self


class DomainPack(Strict):
    schema_version: Literal[1] = 1
    namespace: Token
    version: Version
    entity_types: list[TypeRef] = Field(min_length=1, max_length=40)
    predicates: list[PredicateSpec] = Field(min_length=1, max_length=40)
    dependencies: list[PackRef] = Field(default_factory=list, max_length=4)
    provenance: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unambiguous(self):
        if len(set(self.entity_types)) != len(self.entity_types):
            raise ValueError("Duplicate entity types")
        if any(t.split(":")[0] != self.namespace for t in self.entity_types):
            raise ValueError("A pack may define only its own namespace types")
        if (len({d.namespace for d in self.dependencies}) != len(self.dependencies)
                or self.namespace in {d.namespace for d in self.dependencies}):
            raise ValueError("Dependencies must have distinct foreign namespaces")
        used = set()
        for pred in self.predicates:
            # Names and aliases share a single exact lookup space per version.
            aliases = [surface(a) for a in [pred.name, *pred.aliases]]
            if len(set(aliases)) != len(aliases) or used.intersection(aliases):
                raise ValueError("Conflicting predicate name/alias")
            used.update(aliases)
            allowed = {self.namespace, *[d.namespace for d in self.dependencies]}
            if any(t.split(":")[0] not in allowed for r in pred.roles for t in r.types):
                raise ValueError("Role type requires an explicit pack dependency")
            if any(t.split(":")[0] == self.namespace and t not in self.entity_types
                   for r in pred.roles for t in r.types):
                raise ValueError("Undefined local role type")
        return self

    @property
    def content_hash(self):
        return sha256(json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode()).hexdigest()

    @property
    def ref(self):
        return PackRef(namespace=self.namespace, version=self.version, content_hash=self.content_hash)


class PackRegistration(Strict):
    pack: DomainPack
    authorise_action: bool = False


class MappingChange(Strict):
    assertion_id: Digest
    pack_refs: list[PackRef] = Field(default_factory=list, max_length=4)
    revert_revision_id: Digest | None = None
    expected_binding_id: Digest
    idempotency_key: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=5, max_length=1000)
    authorise_action: bool = False


class SchemaRuntime:
    def __init__(self, store):
        self.store = store

    def load(self, refs):
        refs = [PackRef.model_validate(r) if isinstance(r, dict) else r for r in refs]
        if len(refs) > 4 or len({r.namespace for r in refs}) != len(refs):
            raise ValueError("At most four distinct pinned namespaces per upload")
        packs = []
        for ref in refs:
            record = self.store.get(uid("domain-pack-v1", ref.namespace, ref.version))
            if not record or record["content_hash"] != ref.content_hash:
                raise ValueError("Pinned pack missing/hash mismatch in this dataset")
            packs.append(record)
        return packs

    def register(self, request):
        if not self.store.settings.schema_writes or not request.authorise_action:
            raise ValueError("Pack registration needs operator schema_writes and explicit authorization")
        pack = request.pack
        ident = uid("domain-pack-v1", pack.namespace, pack.version)
        with self.store.transaction():
            old = self.store.get(ident)
            if old:
                if old["content_hash"] != pack.content_hash:
                    raise ValueError("Namespace/version conflict; publish a new immutable version")
                return old
            dependencies = self.load(pack.dependencies)
            known = {t for d in dependencies for t in d["pack"]["entity_types"]} | set(pack.entity_types)
            if any(t not in known for p in pack.predicates for r in p.roles for t in r.types):
                raise ValueError("Dependency type is not defined by its pinned pack")
            counts = self.store.counts()
            if counts.get("DomainPack", 0) >= 100:
                raise ValueError("Domain pack budget exceeded")
            if sum(counts.values())+len(pack.predicates)+1 > 100000:
                raise ValueError("Schema record quota exceeded")
            record = dict(id=ident, kind="DomainPack", content_hash=pack.content_hash,
                          pack=pack.model_dump(), ref=pack.ref.model_dump(), algorithm="domain-pack-v1")
            definitions = [self.definition(record, p) for p in pack.model_dump()["predicates"]]
            self.store.commit([record, *definitions])
            return record

    @staticmethod
    def definition(pack, spec):
        return dict(id=uid("pack-predicate-v1", pack["id"], spec["name"]), kind="PredicateDefinition",
                    namespace=pack["ref"]["namespace"], version=pack["ref"]["version"],
                    pack_id=pack["id"], pack_hash=pack["content_hash"], spec=spec,
                    semantic_state="DECLARED_SCHEMA", registration_basis="operator_declarative_pack",
                    eligible_for_inference=False, algorithm="domain-pack-v1")

    def bind(self, assertions, packs, open_discovery=False):
        """Pure staged bindings. No source or prior interpretation is modified."""
        from .open_relations import scope

        output, cached = [], {}
        for assertion in assertions:
            raw = assertion.get("original_predicate", assertion.get("original_relation_type", ""))
            matches = [(pack, spec) for pack in packs for spec in pack["pack"]["predicates"]
                       if surface(raw) in {surface(a) for a in [spec["name"], *spec["aliases"]]}]
            selected = self.definition(*matches[0]) if len(matches) == 1 else None
            candidates = [self.definition(p, s)["id"] for p,s in matches][:8]
            phrase_scope = scope(raw, assertion.get("original_claim", assertion.get("evidence", "")))
            # Pack aliases do not erase explicit attempted/cancelled scope. A
            # modified phrase remains its own provisional definition.
            if selected and phrase_scope["modifiers"]:
                selected = None
            errors = []
            if selected:
                spec = selected["spec"]
                is_binary = assertion["kind"] == "Claim"
                if is_binary != (spec["form"] == "binary"):
                    errors.append("binary/event shape differs")
                actual = ([dict(role=spec["roles"][0]["name"], entity_type=assertion["subject_type"]),
                           dict(role=spec["roles"][1]["name"], entity_type=assertion["object_type"])]
                          if is_binary else assertion["participants"])
                for role in spec["roles"]:
                    participants = [p for p in actual if p["role"] == role["name"]]
                    if not role["minimum"] <= len(participants) <= role["maximum"]:
                        errors.append("role cardinality: " + role["name"])
                    if any(p["entity_type"] not in role["types"] for p in participants):
                        errors.append("role type: " + role["name"])
                if {p["role"] for p in actual} - {r["name"] for r in spec["roles"]}:
                    errors.append("undeclared participant role")
                for qualifier in QUALIFIERS - set(spec["qualifiers"]):
                    if assertion.get(qualifier) not in (None, False, "unknown", "asserted", "positive"):
                        errors.append("undeclared qualifier: " + qualifier)
            state = "INCOMPATIBLE" if errors else "KNOWN_COMPATIBLE" if selected else "UNRESOLVED"
            if not selected and open_discovery:
                selected = self.provisional(assertion, raw, packs)
                if selected["id"] not in cached:
                    old = self.store.get(selected["id"])
                    cached[selected["id"]] = old or selected
                    if not old:
                        output.append(selected)
                state = "POSSIBLE_ALIAS" if candidates else "PROVISIONAL_NEW"
            binding = dict(id=uid("schema-binding-v2", assertion["id"], [p["ref"] for p in packs], open_discovery),
                           kind="SchemaBinding", assertion_id=assertion["id"],
                           evidence_id=assertion["evidence_id"], source_id=assertion["source_id"],
                           original_phrase=raw, pack_refs=[p["ref"] for p in packs],
                           predicate_definition_id=selected["id"] if selected else None,
                           canonical_name=selected["spec"]["name"] if selected else None,
                           namespace=selected["namespace"] if selected else None,
                           state=state, candidate_definition_ids=candidates,
                           canonicalization_basis="exact_operator_declared_alias_and_shape" if state == "KNOWN_COMPATIBLE"
                           else "literal_surface_only_no_equivalence",
                           source_qualifiers=phrase_scope,
                           errors=errors, eligible_for_inference=False, algorithm="schema-binding-v2")
            # Flat indexed lookup, without injecting a predicate into Cypher.
            binding["block_key"] = binding["predicate_definition_id"] or "unresolved"
            output.append(binding)
            output.append(dict(id=uid("schema-head-v1", assertion["id"]), kind="SchemaBindingHead",
                               assertion_id=assertion["id"], binding_id=binding["id"], version=1, revision_id=None))
            assertion["schema_binding_id"] = binding["id"]
            assertion["eligible_for_inference"] = False
        return output

    @staticmethod
    def provisional(assertion, raw, packs):
        namespace = packs[0]["ref"]["namespace"] if len(packs) == 1 else "open"
        binary = assertion["kind"] == "Claim"
        roles = ([dict(name="subject", types=[assertion["subject_type"]], minimum=1, maximum=1),
                  dict(name="object", types=[assertion["object_type"]], minimum=1, maximum=1)]
                 if binary else [dict(name=role, types=sorted({p["entity_type"] for p in assertion["participants"] if p["role"] == role}),
                                      minimum=1, maximum=12)
                                 for role in sorted({p["role"] for p in assertion["participants"]})])
        name = "OPEN_" + uid(surface(raw), roles)[:16].upper()
        return dict(id=uid("open-predicate-v1", namespace, surface(raw), roles), kind="PredicateDefinition",
                    namespace=namespace, version="1.0.0", pack_id=None, pack_hash=None,
                    original_surface=raw, spec=dict(name=name, definition="Literal source phrase '"+raw+
                    "'; roles preserve its observed argument orientation. Semantic equivalence is unvalidated.",
                    form="binary" if binary else "event", direction="directed" if binary else "collective",
                    roles=roles, aliases=[], qualifiers=sorted(QUALIFIERS)),
                    semantic_state="PROVISIONAL", registration_basis="source_grounded_literal_frame",
                    eligible_for_inference=False, algorithm="open-predicate-v1")

    def current(self, assertion):
        head = self.store.get(uid("schema-head-v1", assertion["id"]))
        return head or dict(id=uid("schema-head-v1", assertion["id"]), kind="SchemaBindingHead",
                            assertion_id=assertion["id"], binding_id=assertion.get("schema_binding_id"),
                            version=0, revision_id=None)

    def revise(self, request, actor):
        if not self.store.settings.schema_writes or not request.authorise_action:
            raise ValueError("Schema revision needs operator opt-in and explicit authorization")
        with self.store.transaction():
            ident = uid("schema-revision-v1", request.idempotency_key)
            request_hash = uid(request.model_dump(), actor)
            old = self.store.get(ident)
            if old:
                if old.get("request_hash") != request_hash:
                    raise ValueError("Schema idempotency key conflict")
                return old
            assertion = self.store.get(request.assertion_id)
            if not assertion or assertion["kind"] not in {"Claim", "RelationEvent"}:
                raise ValueError("Assertion missing in this dataset")
            previous = self.current(assertion)
            if previous["binding_id"] != request.expected_binding_id or previous["version"] >= 100:
                raise ValueError("Stale schema revision or history budget exceeded")
            if request.revert_revision_id:
                target = self.store.get(request.revert_revision_id)
                if (not target or target["kind"] != "SchemaMappingRevision"
                        or target["assertion_id"] != assertion["id"] or target["id"] != previous["revision_id"]
                        or request.pack_refs):
                    raise ValueError("Cannot revert over a later/unrelated schema revision")
                binding_id, staged = target["previous_binding_id"], []
            else:
                staged = self.bind([dict(assertion)], self.load(request.pack_refs), True)
                binding_id = next(r["id"] for r in staged if r["kind"] == "SchemaBinding")
                staged = [r for r in staged if r["kind"] != "SchemaBindingHead"]
            if binding_id == previous["binding_id"]:
                raise ValueError("Schema revision would not change the interpretation")
            revision = dict(id=ident, kind="SchemaMappingRevision", request_hash=request_hash,
                            assertion_id=assertion["id"], previous_binding_id=previous["binding_id"],
                            binding_id=binding_id, previous_revision_id=previous["revision_id"],
                            reverts_id=request.revert_revision_id, reason=request.reason, actor=actor,
                            recorded_at=now(), eligible_for_inference=False,
                            invalidation="Consumers must compare their exact consumed binding ID; no semantic recompute")
            head = {**previous, "binding_id":binding_id, "revision_id":ident, "version":previous["version"]+1}
            if sum(self.store.counts().values())+len(staged)+2 > 100000:
                raise ValueError("Schema record budget exceeded")
            self.store.commit([*staged, revision, head])
            return revision

    def assertions(self, definition_id, limit=100):
        if not 1 <= limit <= 200:
            raise ValueError("Schema retrieval limit exceeded")
        if self.store.client:
            rows = self.store.query("MATCH (b:SchemaBinding) WHERE b.block_key=$key RETURN b.payload LIMIT "
                                    + str(limit+1), {"key": definition_id})
            bindings = [json.loads(r[0]) for r in rows]
        else:
            bindings = [b for b in self.store.list("SchemaBinding", 20000) if b["block_key"] == definition_id][:limit+1]
        items = []
        for binding in bindings[:limit]:
            assertion = self.store.get(binding["assertion_id"])
            current = self.current(assertion)
            items.append(dict(binding=binding, assertion=assertion, evidence=self.store.get(binding["evidence_id"]),
                              current=current["binding_id"] == binding["id"], current_binding_id=current["binding_id"],
                              assertion_state="UNKNOWN" if assertion["modality"] != "asserted"
                              else "SOURCE_NEGATED" if assertion["polarity"] == "negative" else "SOURCE_ASSERTED",
                              qualified_source=assertion["modality"] != "asserted"))
        return dict(truncated=len(bindings) > limit, items=items,
                    semantics="Historical and current source interpretations, not independent truth or enabled rules")
