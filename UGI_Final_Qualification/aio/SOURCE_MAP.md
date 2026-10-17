# Code provenance

- `ugi_rulebook/*`: new original state-machine rulebook, experiment driver and tests.
- `ugi_real_track1/*`: preserved prior real GitHub source adapters, SHA256-pinned snapshots and benchmark definitions. The manifest reader handles explicit Compose `depends_on` only.
- `ugi_krish_validation_v2/*`: preserved earlier read-only analytics and actual MCP stdio transport used for test compatibility.
- `ugi_agent_fix/*`: preserved prior strict legacy Qwen agent benchmark and guarded engine-explanation patcher used only on Docker `/tmp` copy.

No main `ugi/` package is shipped in this ZIP; this suite calls the existing repository's UGI version inside Docker. Do not install any experiment modules to production or commit these results to the repository without reviewing their provenance and scope.

- Rulebook ZIP v2.1: patch_engine.py now synchronized with Agent Fix v2; added split-line branch regression and runtime version check.
