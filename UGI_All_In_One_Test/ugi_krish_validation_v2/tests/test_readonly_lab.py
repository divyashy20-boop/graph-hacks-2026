import unittest
from ugi_krish_validation_v2.analytics import projection, shortest_path, components, pagerank
from ugi_krish_validation_v2.freshness import classify_freshness
from ugi_krish_validation_v2.planner import plan_readonly
from ugi_krish_validation_v2.read_only_store import is_read_only_cypher
from ugi_krish_validation_v2.run import fixture, offline

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.e, self.c = fixture()

    def test_offline_path_and_read_only(self):
        r=offline()
        self.assertEqual(r['shortest_path']['claim_ids'],['c1','c2'])
        self.assertFalse(r['stale_guard_demo']['stale']['allow'])
        self.assertFalse(r['stale_guard_demo']['unchanged_identity']['allow'])
        self.assertFalse(r['stale_guard_demo']['unknown']['allow'])

    def test_negative_speculative_historical_excluded(self):
        v=projection(self.e,self.c,as_of='2026-10-16',allow_predicates=('DEPENDS_ON','USES'))
        exclusions={z['claim_id']:z['reason'] for z in v['excluded']}
        self.assertEqual(exclusions['c4'],'negative_or_unknown_polarity')
        self.assertEqual(exclusions['c3'],'directly_contradicted')
        self.assertEqual(exclusions['c5'],'non_asserted_modality')
        self.assertEqual(exclusions['c6'],'inactive_for_requested_time')

    def test_no_temporally_incompatible_path(self):
        a=[dict(id='1',name='A'),dict(id='2',name='B'),dict(id='3',name='C')]
        cs=[dict(id='a',subject_id='1',object_id='2',predicate='P',valid_from='2020-01-01',valid_to='2020-12-31'),
            dict(id='b',subject_id='2',object_id='3',predicate='P',valid_from='2022-01-01',valid_to='2022-12-31')]
        # Date-free probe would exclude past edges; explicit historical evaluation still requires shared dates.
        v=projection(a,cs,as_of='2020-06-01',allow_predicates=('P',))
        self.assertFalse(shortest_path(v,'1','3')['found'])

    def test_schema_bound_claim_excluded(self):
        v=projection(self.e,self.c,blocked_assertion_ids={'c1'})
        self.assertEqual(v['included_count'],1)
        self.assertFalse(shortest_path(v,'Checkout','Cache')['found'])

    def test_order_and_scores(self):
        v=projection(self.e,self.c)
        rank=pagerank(v)
        self.assertEqual(len(rank['rankings']),5)
        self.assertAlmostEqual(sum(x['score'] for x in rank['rankings']),1,places=6)
        comps=components(v)
        self.assertEqual(comps['kind'],'weakly_connected_components')
        self.assertEqual(comps['components'][0],['Cache','Checkout','Gateway'])

    def test_planner_only_read_tools(self):
        plan=plan_readonly('Cache','Checkout','Cache')
        self.assertEqual([x['tool'] for x in plan],['search_entities','evaluate_relationship'])
        self.assertFalse(any('create' in x['tool'] for x in plan))

    def test_missing_identity_blocks(self):
        self.assertEqual(classify_freshness(None)['state'],'BLOCK_UNKNOWN')
        self.assertEqual(classify_freshness({'kind':'DerivedArtifact'},None)['state'],'BLOCK_UNVERIFIED')
        self.assertEqual(classify_freshness({'kind':'DerivedArtifact'},{'state':'stale'})['state'],'BLOCK_STALE')
        self.assertEqual(classify_freshness({'kind':'DerivedArtifact'},{'state':'current_inputs_only'})['state'],'IDENTITY_INPUTS_CURRENT_ONLY')

    def test_read_only_cypher_gate(self):
        self.assertTrue(is_read_only_cypher('MATCH (c:Claim) RETURN c.payload LIMIT 10'))
        for unsafe in ('CREATE INDEX FOR (n:Record) ON (n.id)',
                       'MATCH (n) DETACH DELETE n',
                       'MATCH (n) SET n.p = 1 RETURN n',
                       'CALL db.labels()',
                       'MATCH (n) WITH n MERGE (x:Other {id:1}) RETURN x'):
            self.assertFalse(is_read_only_cypher(unsafe), unsafe)

    def test_fail_closed_on_large_input(self):
        a=[{'id':str(i)} for i in range(1202)]
        with self.assertRaisesRegex(ValueError,'budget'):
            projection(a,[])

if __name__=='__main__':unittest.main()
