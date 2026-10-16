from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from redis.exceptions import RedisError

from .engine import Engine
from .identity import ArtifactRequest, IdentityChange
from .models import InvestigationRequest, RelationQuery, ReviewDecision, Settings, now, uid
from .resolution import AuthorityObservation, IdentityResolver
from .store import Store


def create_app(settings=None):
    settings = settings or Settings()
    app = FastAPI(title="Universal Graph Intelligence", version="1.0.0")
    ingestion_slots = BoundedSemaphore(2)

    @lru_cache(maxsize=64)
    def store_for(owner, dataset):
        return Store(settings, owner, dataset)

    def context(
        x_api_key: str = Header(default=""),
        x_dataset: str = Header(default="demo", min_length=1, max_length=60,
                               pattern=r"^[a-zA-Z0-9_-]+$"),
    ):
        if settings.api_keys:
            allowed = [s.strip() for s in settings.api_keys.split(",") if s.strip()]
            if not any(secrets.compare_digest(x_api_key, candidate) for candidate in allowed):
                raise HTTPException(401, "Valid API key required")
            owner = uid(x_api_key)[:24]
        else:
            owner = "local"
        store = store_for(owner, x_dataset)
        store.consume("http:" + owner + ":" + now()[:16], settings.requests_per_minute)
        return Engine(store)

    @app.exception_handler(ValueError)
    def invalid(_, exc):
        message = str(exc)
        return JSONResponse(status_code=429 if "quota" in message.lower() else 422,
                            content={"detail": message})

    @app.exception_handler(RedisError)
    def graph_unavailable(_, exc):
        message = ("Graph execution budget exceeded; reduce upload size or query scope. "
                   "No successful write has been confirmed; inspect the dataset before retrying."
                   if "timed out" in str(exc).lower() else "Graph storage unavailable")
        return JSONResponse(status_code=503, content={"detail": message,
                                                     "error_type": type(exc).__name__})

    @app.get("/", response_class=HTMLResponse)
    def home():
        return Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    @app.get("/assets/{filename}")
    def asset(filename: str):
        if filename not in {"app.js", "style.css"}:
            raise HTTPException(404, "Asset not found")
        return FileResponse(Path(__file__).with_name("assets") / filename)

    @app.get("/health")
    def health():
        return {"service": "ugi", "backend": settings.backend,
                "provider": settings.provider, "live_inference_verified": False}

    @app.get("/ready")
    def ready(engine=Depends(context)):
        return {"ready": engine.store.ping()}

    @app.post("/api/uploads")
    async def upload(file: UploadFile = File(), use_ai: bool = False, engine=Depends(context)):
        content = await file.read(settings.max_upload_bytes + 1)
        await file.close()
        # CPU/model work executes in the thread pool, not on the event loop.
        from starlette.concurrency import run_in_threadpool

        def ingest_bounded():
            if not ingestion_slots.acquire(blocking=False):
                raise HTTPException(429, "Two uploads already processing")
            try:
                return engine.ingest(file.filename or "", content, use_ai)
            finally:
                ingestion_slots.release()

        return await run_in_threadpool(ingest_bounded)

    @app.get("/api/graph")
    def graph(limit: int = Query(250, ge=1, le=500),
              as_of: str | None = Query(default=None, max_length=10), engine=Depends(context)):
        from datetime import date

        from .engine import active

        if as_of:
            date.fromisoformat(as_of)
        entities = engine.store.list("Entity", limit)
        ids = {e["id"] for e in entities}
        claims = [c for c in engine.store.list("Claim", limit) if c["subject_id"] in ids
                  and c["object_id"] in ids and (not as_of or active(c, as_of))]
        events = [e for e in engine.store.events(limit=limit)
                  if all(p["entity_id"] in ids for p in e["participants"])
                  and (not as_of or active(e, as_of))]
        return {"entities": entities, "claims": claims, "events": events,
                "counts": engine.store.counts(),
                "as_of": as_of, "unknown_dates_excluded": bool(as_of),
                "truncated": any(engine.store.counts().get(kind, 0) > limit
                                 for kind in ("Entity", "Claim", "RelationEvent"))}

    @app.get("/api/events")
    def events(entity_id: str | None = Query(default=None, max_length=160),
               as_of: str | None = Query(default=None, max_length=32),
               limit: int = Query(100, ge=1, le=500), engine=Depends(context)):
        from datetime import date

        from .engine import active

        if as_of:
            date.fromisoformat(as_of)
        records = engine.store.events(entity_id, limit)
        return {"events": [e for e in records if not as_of or active(e, as_of)],
                "limit": limit, "filtered_after_limit": bool(as_of),
                "semantics": "Whole source events; participation does not prove binary predicates"}

    @app.get("/api/entities")
    def entities(name: str = Query(min_length=1, max_length=160), engine=Depends(context)):
        return engine.store.entities(name)

    @app.get("/api/records/{record_id}")
    def record(record_id: str, engine=Depends(context)):
        item = engine.store.get(record_id)
        if not item:
            raise HTTPException(404, "Record not found")
        return item

    @app.get("/api/identity/cards/{entity_id}")
    def identity_card(entity_id: str, as_known_at: str | None = Query(default=None, max_length=40),
                      engine=Depends(context)):
        from .identity import IdentityLedger

        return IdentityLedger(engine.store).card(entity_id, as_known_at)

    def identity_writer(engine):
        from .identity import IdentityLedger

        if not settings.identity_ledger:
            raise HTTPException(403, "Identity ledger writes require UGI_IDENTITY_LEDGER=true")
        return IdentityLedger(engine.store)

    @app.post("/api/identity/revisions")
    def identity_revision(request: IdentityChange, engine=Depends(context)):
        return identity_writer(engine).revise(request, engine.store.owner)

    @app.post("/api/identity/artifacts")
    def identity_artifact(request: ArtifactRequest, engine=Depends(context)):
        return identity_writer(engine).artifact(request)

    @app.get("/api/identity/artifacts/{artifact_id}")
    def identity_freshness(artifact_id: str, engine=Depends(context)):
        from .identity import IdentityLedger

        return IdentityLedger(engine.store).freshness(artifact_id)

    @app.get("/api/identity/candidates/{snapshot_id}")
    def identity_candidates(snapshot_id: str, engine=Depends(context)):
        with engine.store.transaction():
            return IdentityResolver(engine.store).candidates(snapshot_id)

    @app.get("/api/identity/compare")
    def identity_compare(left: str = Query(min_length=1, max_length=160),
                         right: str = Query(min_length=1, max_length=160), engine=Depends(context)):
        with engine.store.transaction():
            return IdentityResolver(engine.store).compare(left, right)

    @app.post("/api/identity/authority-observations")
    def identity_observation(request: AuthorityObservation, engine=Depends(context)):
        identity_writer(engine)
        return IdentityResolver(engine.store).observe(request, engine.store.owner)

    @app.get("/api/tasks")
    def tasks(engine=Depends(context)):
        return engine.store.list("ReviewTask")

    @app.get("/api/investigations")
    def cases(engine=Depends(context)):
        return engine.store.list("Investigation")

    @app.post("/api/relationships")
    def relationship(query: RelationQuery, engine=Depends(context)):
        return engine.relationship(query)

    @app.post("/api/investigations")
    def investigate(request: InvestigationRequest, engine=Depends(context)):
        return engine.investigate(request, engine.store.owner)

    @app.post("/api/tasks/{task_id}/decision")
    def decide(task_id: str, decision: ReviewDecision, engine=Depends(context)):
        with engine.store.transaction():
            task = engine.store.get(task_id)
            if not task or task["kind"] != "ReviewTask":
                raise HTTPException(404, "Review task not found")
            if task["status"] != "open":
                raise HTTPException(409, "Task already reviewed")
            task.update(status=decision.decision, decision_reason=decision.reason,
                        reviewer=engine.store.owner, reviewed_at=now())
            action = dict(id=uid(task_id, "decision"), kind="AgentAction", operation="review_decision",
                          task_id=task_id, actor=engine.store.owner, state="executed",
                          recorded_at=now(), decision=decision.decision)
            engine.store.commit([task, action])
        return task

    @app.get("/api/tools")
    def tools(engine=Depends(context)):
        return {"planner": "bounded deterministic graph policy", "max_steps": settings.max_tool_steps,
                "read_only": ["resolve_identity", "retrieve_claims", "reverse_dependency_paths",
                              "find_conflicts", "relationship_without_hypothesis"],
                "writes": ["create_investigation_and_reviews", "review_decision", "create_hypothesis"],
                "external_actions": [], "arbitrary_cypher": False}

    app.state.store_for = store_for
    app.state.settings = settings
    return app


app = create_app()
