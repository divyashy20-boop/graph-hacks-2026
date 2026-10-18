# Graphynx UI / Groq P2 compatibility release

This branch combines the latest `main` hero/background UI, `UI-krish-changes` 3D force-graph integration, and Groq GPT-OSS 120B P2 source code. UI graph refresh now tolerates secondary investigation/review endpoints failing independently, handles non-JSON gateway responses, and accurately labels empty datasets.

## Why demo cards can appear empty

The three built-in datasets `showcase-b-incident`, `showcase-b-supply`, and `showcase-b-research` auto-seed only with `UGI_BACKEND=memory`. On persistent FalkorDB, selecting a preset changes the active dataset but does not insert any sample documents. Real claims, cases and review queues are populated by actual uploads or persisted demo fixtures; never present placeholder cards as verified results.

After checking the target owner/API key and confirming you want to write example records to the intended FalkorDB database, run this in the candidate container:

```sh
python -m ugi.seed_demo --dataset showcase-b-incident --confirm-falkordb
python -m ugi.seed_demo --dataset showcase-b-supply --confirm-falkordb
python -m ugi.seed_demo --dataset showcase-b-research --confirm-falkordb
```

If the HTTP gateway uses a different authorized key in `UGI_API_KEYS`, select its zero-based index using `--key-index N`. The key is never logged. This operator command skips nonempty datasets and explicitly uses `use_ai=False`.

## AWS production warning

The EC2 production image includes custom judge API route `/api/agent/ai-search`, `budget_guard.py`, and a DynamoDB lifetime budget reservation absent from the public GitHub branches. The current EC2 image is **not** equivalent to this GitHub branch. NEVER replace the running image from this checkout without reapplying/verifying the production-only API and provider budget patches and retaining rollback. The bundled Groq provider code in GitHub does not establish that production DynamoDB protections were carried into the source branch.

The public Amplify site contains its own `gateway.js` and `agent.js` not present in the repo. Website judge-code gating and API Gateway/Lambda proxy are separate from the backend `UGI_API_KEYS` authorization. AWS role on EC2 currently cannot edit Amplify or CloudFormation (AccessDenied). For a single open website, remove the visitor gate at the hosting/gateway level **without publishing API keys in frontend JS**; keep the existing server-side cost, request and upload limits. Authorization design and final public deployment still require review against the actual gateway.

## Verification before promotion

Run `python -m pytest -q` and `node --test tests/test_force_graph.cjs` on this branch, then smoke test on a non-production dataset with an authenticated gateway: dashboard populated/empty, 2D/3D fallback, source inspector, offline upload, graph relations, investigations, review decisions and guided receipts. Check that temporary review failures show a warning while the graph still loads. Verify public Amplify HTML and JS separately after its deployment. This branch is pushed for integration review; it is **not** a public-site deployment.
