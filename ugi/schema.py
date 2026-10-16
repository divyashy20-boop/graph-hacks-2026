"""Declarative vocabularies. Shape validity is not factual or logical validity."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import Strict, uid

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
            if self.store.counts().get("DomainPack", 0) >= 100:
                raise ValueError("Domain pack budget exceeded")
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

    def bind(self, assertions, packs):
        """Pure staged bindings. No source or prior interpretation is modified."""
        output = []
        for assertion in assertions:
            raw = assertion.get("original_predicate", assertion.get("original_relation_type", ""))
            matches = [(pack, spec) for pack in packs for spec in pack["pack"]["predicates"]
                       if surface(raw) in {surface(a) for a in [spec["name"], *spec["aliases"]]}]
            selected = self.definition(*matches[0]) if len(matches) == 1 else None
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
            binding = dict(id=uid("schema-binding-v1", assertion["id"], [p["ref"] for p in packs]),
                           kind="SchemaBinding", assertion_id=assertion["id"],
                           evidence_id=assertion["evidence_id"], source_id=assertion["source_id"],
                           original_phrase=raw, pack_refs=[p["ref"] for p in packs],
                           predicate_definition_id=selected["id"] if selected else None,
                           canonical_name=selected["spec"]["name"] if selected else None,
                           namespace=selected["namespace"] if selected else None,
                           state="INCOMPATIBLE" if errors else "KNOWN_COMPATIBLE" if selected else "UNRESOLVED",
                           errors=errors, eligible_for_inference=False, algorithm="schema-binding-v1")
            # Flat indexed lookup, without injecting a predicate into Cypher.
            binding["block_key"] = binding["predicate_definition_id"] or "unresolved"
            output.append(binding)
            assertion["schema_binding_id"] = binding["id"]
            assertion["eligible_for_inference"] = False
        return output

    def assertions(self, definition_id, limit=100):
        if not 1 <= limit <= 200:
            raise ValueError("Schema retrieval limit exceeded")
        if self.store.client:
            rows = self.store.query("MATCH (b:SchemaBinding) WHERE b.block_key=$key RETURN b.payload LIMIT "
                                    + str(limit+1), {"key": definition_id})
            bindings = [json.loads(r[0]) for r in rows]
        else:
            bindings = [b for b in self.store.list("SchemaBinding", 20000) if b["block_key"] == definition_id][:limit+1]
        return dict(truncated=len(bindings) > limit,
                    items=[dict(binding=b, assertion=self.store.get(b["assertion_id"]),
                                evidence=self.store.get(b["evidence_id"])) for b in bindings[:limit]],
                    semantics="Version-pinned source assertions, not independent truth or enabled rules")
