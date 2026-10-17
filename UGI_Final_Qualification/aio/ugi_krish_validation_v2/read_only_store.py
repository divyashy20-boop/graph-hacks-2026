"""Open the existing UGI graph without running Store.__init__ index CREATE calls.

Only safe read-only Cypher is allowed. UGI schema queries are trusted application
code, but we still block all write Cypher and any Store.commit/transaction writes.
"""
from __future__ import annotations
import re
from contextlib import contextmanager

_DISALLOWED = re.compile(r'\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD|CALL|INDEX)\b',re.I)


def is_read_only_cypher(text):
    stripped = text.strip()
    return (stripped.upper().startswith(('MATCH ', 'RETURN ', 'OPTIONAL MATCH '))
            and not _DISALLOWED.search(stripped))


def read_only_store(settings, dataset, owner='local'):
    from redis import Redis
    from ugi.store import Store
    from ugi.models import uid

    class ReadOnlyStore(Store):
        def __init__(self):
            # Bypass Store.__init__, because it issues CREATE INDEX on every instance.
            self.settings=settings
            self.owner=owner
            self.graph=settings.graph_prefix + '_' + uid(owner,dataset)[:24]
            self.client=Redis.from_url(settings.redis_url,decode_responses=True,
                                        socket_connect_timeout=3,socket_timeout=15)
            self.records={}
            self.links=set()

        def query(self, text, params=None):
            if not is_read_only_cypher(text):
                raise PermissionError('Read-only lab blocks all Cypher mutations')
            return super().query(text, params)

        def commit(self, *args, **kwargs):
            raise PermissionError('Read-only lab cannot persist records')

        @contextmanager
        def transaction(self):
            # No Redis lease write. Reading while concurrent writers work is
            # a best-effort snapshot; trial output must not imply atomic isolation.
            yield

    return ReadOnlyStore()
