# UGI Rulebook — enforced at runtime

| Phase | Preconditions | Permitted action | Postcondition |
|---|---|---|---|
| A. Parse | User gave explicit service relationship | Separate selected dataset from the two entity names and requested predicate | Unique `Intent` or safe abstention |
| B. Resolve subject | Subject unresolved | `search_entities({"name": "<subject>"})` | Exactly one matching graph entity |
| C. Resolve object | Object unresolved | `search_entities({"name": "<object>"})` | Exactly one matching graph entity |
| D. Evaluate | Both identities resolved | `evaluate_relationship` with verified subject/object and approved predicate | Structured engine verdict and zero or more exact claim IDs |
| E. Verify | Claim IDs returned by relation tool | `get_claim_evidence({"claim_id": "<returned ID>"})` for *each* ID | Claim ID, evidence ID, source ID and source quote must match |
| F. Preview (optional) | User explicitly requested investigation preview | `investigate_dependency_incident` with `authorise_action: false` | Must return `executed: false` |
| G. Finish | Every required phase complete | Render only engine-derived verdict and evidence IDs | Consistent final answer with uncertainty |

## Decision authority

- **Code** selects the mandatory phase and builds every MCP argument from graph results and interpreted user request, never from a free-form LLM call.
- **LLM** may advise next tool (optional); those suggestions never override the rulebook. Wrong suggestions are scored separately. A future schema-constrained model interpreter can replace the deliberately narrow parser after independent evaluation.
- **Database** provides source assertions; the controller never invents relationship truth, raw evidence, claim IDs, causal incidents or external world facts.
- **Policy** refuses destructive requests, ambiguous entities, malformed tool schemas, contradictory rule conclusions, fabricated evidence, mismatching citations and unauthorized writes.
- **Budgets:** max 12 MCP calls per request; evidence list max 100, entities max 1,200, user query max 2,000 characters; no automatic retries outside this bound.

## Non-supported intent classes

Arbitrary causal assertions, prose OpenIE, entity fusion, uncertain direction, more than two candidate entities and all external side effects are **not** silently approximated. They return a structured abstention or incomplete status.

## Honest labels

`benchmark_pass=true` means the **guided rulebook** completed required graph calls and reproduced the annotated result on that test case. It does **not** indicate the LLM autonomously selected the executed tools or their arguments. Model suggestions and a full model-selected legacy benchmark are reported independently when enabled.
