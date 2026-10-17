# After this final test: integration → release → AWS (not performed by this suite)

**Only after** `FINAL_DECISION.json` reports `QUALIFIED_FOR_FEATURE_FLAGGED_INTEGRATION`:

1. Freeze a clean Git commit of host H1 work and existing UGI tests, backup existing graphs before migrations. No force push or silent overwrite.
2. Add the rulebook as an optional API/MCP workflow controller with runtime tool-schema introspection, tenant scoping, bounded budget, explicit abstentions and no persistent actions by default. Use the verified graph answer as the source of truth.
3. Add a durable per-tenant receipt registry and **enforce** automatic observation capture for every graph-read surface: agent controller, REST endpoints, MCP server, background jobs and cache. Do not rely on LLM self-reports. Track negative queries, source version IDs, temporal scope and query footprints.
4. Add an authoritative graph revision/event stream and transactional outbox for cross-system knowledge changes. Every read receipt must bind to an auditable graph revision; stale/UNKNOWN blocks reuse. Design fencing or transactional internal executor with idempotency + revalidation. **Do not enable external actions based on SQLite gate alone.**
5. Build genuinely unseen external benchmark data and adversarial tests for natural-language H1 extraction, ambiguous identity, contradiction semantics, snapshots, read-your-writes, retries, rate limiting and multi-process races.
6. Perform actual end-to-end tests through user-facing UI/API, not just standalone scripts; verify evidence links, status UI, auth boundaries, handling of unsupported questions, regression traces and degraded/Ollama-unavailable behavior.
7. AWS deployment only after hardened permissions/IAM, Secrets Manager, HTTPS/API authentication, tenant isolation, observability, backups and rollback procedures. Use AWS resources only with explicit cost authorization; do not deploy or charge accounts from this test package.

If final combined graph-memory test fails, prioritize that failure rather than merging every prototype. If it passes but external-action atomicity remains unimplemented, integrate read-only dynamic memory first and keep actions disabled.
