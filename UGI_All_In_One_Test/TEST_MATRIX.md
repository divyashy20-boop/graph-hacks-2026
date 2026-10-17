# Test matrix and interpretation

| Layer | Tests | Status in authoring container |
|---|---|---|
| Narrow controller / parsing / unsafe / MCP schemas / mocked traces | 37 unit methods (many subtests) | Pass |
| Public manifest parser and source hashing | 10 unit methods | Pass |
| Analytics, freshness, readonly and scoring lab | 14 unit methods | Pass |
| Guarded patcher / compatible source patterns | 5 unit methods | Pass |
| Old orchestrator regression tests | 4 unit methods | Pass |
| Manual 5-source manifest query audit | 26 graph queries | Windows run needed |
| Guided controller with evidence+preview | 10 real MCP workflows | Windows run needed; prior v2 observed 10/10 |
| Extended real source controller | 39 real MCP workflows | All 39 mocked, live Windows run needed |
| Real local Qwen tool advisory | 30 nonbinding suggestions if model available | Windows run needed; prior 10/30 agreement |
| Old Qwen strict baseline | 10 workflows if `-RunLegacyAgent` | Windows run needed; prior 0/10 |
| Ephemeral explanation repair regression | 1 test on copied UGI | Windows run needed; prior v2 pass |

One scenario may involve multiple MCP requests; do not treat the number of tests as unique external source records.

PASS on negative/unknown query means the controller correctly declined to prove a dependency, not that an adverse fact was proved.
