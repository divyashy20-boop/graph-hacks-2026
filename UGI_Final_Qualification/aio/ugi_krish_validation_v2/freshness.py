"""Track2-inspired deny-stale guard: read-only decision, NEVER performs a write.

The existing UGI identity ledger only tracks registered identity dependencies.
A 'current_inputs_only' result MUST NOT be reported as a general fresh artifact.
"""
from __future__ import annotations


def classify_freshness(artifact, freshness=None):
    if not isinstance(artifact, dict) or artifact.get('kind') != 'DerivedArtifact':
        return {'allow': False, 'state': 'BLOCK_UNKNOWN', 'reason': 'Missing or unregistered artifact'}
    if not isinstance(freshness, dict) or freshness.get('state') not in ('stale','current_inputs_only'):
        return {'allow': False, 'state': 'BLOCK_UNVERIFIED',
                'reason': 'Cannot verify registered identity dependencies'}
    if freshness['state'] == 'stale' or freshness.get('changed_mention_snapshot_ids'):
        return {'allow': False, 'state': 'BLOCK_STALE',
                'changed_mentions': freshness.get('changed_mention_snapshot_ids', []),
                'reason': 'Referenced identity assignment changed; re-evaluate first'}
    return {'allow': False, 'state': 'IDENTITY_INPUTS_CURRENT_ONLY',
            'reason': 'Registered identity inputs unchanged; content correctness, source freshness, and other dependencies NOT verified. Not authorized to act.'}


def inspect_ugi_artifact(store, artifact_id):
    """Actual UGI identity-ledger adapter; only get/compare, no revalidation claims."""
    try:
        from ugi.identity import IdentityLedger
        artifact = store.get(artifact_id)
        if not artifact or artifact.get('kind') != 'DerivedArtifact':
            return classify_freshness(None)
        fresh = IdentityLedger(store).freshness(artifact_id)
        return classify_freshness(artifact, fresh)
    except Exception as e:
        return {'allow': False, 'state': 'BLOCK_UNVERIFIED',
                'reason': f'Identity dependency assessment unavailable ({type(e).__name__})'}
