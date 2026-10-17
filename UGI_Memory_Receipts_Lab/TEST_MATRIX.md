# Acceptance scenarios

- T1 Python API signature change (three-argument expansion): stale + action blocked
- T2 JSON unrelated field change: unaffected receipt stays valid
- T3 Absent graph relationship becomes present: absence receipt stale + blocked
- T4 Two conflicting sources: unknown + action blocked
- T5 A -> B -> C receipt chain: cascading invalidation
- T6 Update between earlier check and internal action: blocked
- T7 Out-of-order valid-time correction: stale
- T8 Knowledge-time replay reconstructs old state
- T9 Scoped negative prefix scan: new matching record invalidates
- T10 Source-scoped retraction: stale
- T11 Validity interval expires without new input: scheduled sweep stales
- T12 Replay idempotency
- T13 Verified internal atomic action succeeds
- T14 Multi-field atomic source update
- T15 Cross-tenant isolation
- T16 Atomic internal action ledger
- T17 250 dependent receipts invalidated from one hot fact, latency reported

The unit suite additionally probes 40 concurrent update/action races; 80 seeded randomized field-change pairs; eight simultaneous duplicate-action submissions; 350-receipt fanout; concurrent publishers; SQL-looking names; Unicode; parent-scope violations; duplicate event IDs; unknown-at-seal behavior; JSON Pointer escaping and Python AST variations.
