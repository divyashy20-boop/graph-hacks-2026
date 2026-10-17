"""Run with the PATCHED ugi package active (not against the untouched baseline)."""
import unittest
from ugi.engine import Engine
from ugi.models import RelationQuery, Settings
from ugi.store import Store
import json
class EngineExplanationIntegration(unittest.TestCase):
    def test_transitive_proof_has_consistent_resolution(self):
        st=Store(Settings(backend='memory',provider='offline'),dataset='isolated-explain')
        rows=[{'subject':'Front','subject_type':'Service','subject_id':'svc:front',
               'predicate':'depends on','object':'Mid','object_type':'Service','object_id':'svc:mid'},
              {'subject':'Mid','subject_type':'Service','subject_id':'svc:mid',
               'predicate':'depends on','object':'Back','object_type':'Service','object_id':'svc:back'}]
        Engine(st).ingest('test.json',json.dumps(rows).encode())
        en=Engine(st)
        result=en.relationship(RelationQuery(subject='Front',object='Back',predicate='TRANSITIVELY_DEPENDS_ON'))
        self.assertEqual(result['status'],'RULE_DERIVED')
        self.assertEqual(result['resolution']['assessment'],'RULE_DERIVED_FROM_DEPENDENCIES')
        self.assertEqual(len(result['resolution']['proof_claim_ids']),2)
        self.assertEqual(result['resolution']['missing_evidence'],[])
        reverse=en.relationship(RelationQuery(subject='Back',object='Front',predicate='DEPENDS_ON'))
        self.assertNotIn(reverse['status'],('SOURCE_ASSERTED','RULE_DERIVED'))
        direct=en.relationship(RelationQuery(subject='Front',object='Mid',predicate='DEPENDS_ON'))
        self.assertEqual(direct['status'],'SOURCE_ASSERTED')
if __name__=='__main__':unittest.main()
