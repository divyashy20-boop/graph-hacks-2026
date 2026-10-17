import unittest
from ugi_real_track1.manifest import SOURCES, load_manifest, extract_explicit_dependencies, generate_questions, directed_reachable

class RealSourceTests(unittest.TestCase):
    def test_all_5_pinned_snapshots_match_annotated_dependency_sets(self):
        for source in SOURCES['sources']:
            with self.subTest(name=source['name']):
                services,links=extract_explicit_dependencies(load_manifest(source))
                self.assertEqual({(l['subject'],l['object']) for l in links},
                                 {tuple(x) for x in source['expected_edges']})
                self.assertTrue(services)
    def test_questions_not_generated_from_ugi_outputs(self):
        self.assertGreaterEqual(sum(len(generate_questions(s)) for s in SOURCES['sources']),25)
    def test_false_reverse_dependency(self):
        self.assertIsNone(directed_reachable([('proxy','backend'),('backend','db')],'db','proxy'))
    def test_true_multi_hop(self):
        self.assertEqual(directed_reachable([('proxy','backend'),('backend','db')],'proxy','db'),2)
    def test_reject_unsupported_inline_yaml(self):
        with self.assertRaisesRegex(ValueError,'unsupported'):
            extract_explicit_dependencies('services:\n  a:\n    depends_on: [b]\n  b:\n    image: redis\n')
    def test_reject_nonexistent_target(self):
        with self.assertRaisesRegex(ValueError,'Invalid'):
            extract_explicit_dependencies('services:\n  a:\n    depends_on:\n      - unknown\n')
    def test_ignore_network_names(self):
        services,links=extract_explicit_dependencies('services:\n  app:\n    networks:\n      - dbnet\n  db:\n    networks:\n      - dbnet\n')
        self.assertEqual(links,[])
    def test_mapping_attributes_are_not_fake_dependencies(self):
        example = ('services:\n  app:\n    depends_on:\n      db:\n'
                   '        condition: service_healthy\n        restart: true\n'
                   '  db:\n    image: postgres\n')
        names, links = extract_explicit_dependencies(example)
        self.assertEqual({(x['subject'], x['object']) for x in links}, {('app', 'db')})
    def test_source_has_real_github_identity(self):
        self.assertEqual(SOURCES['source_repository'], 'https://github.com/docker/awesome-compose')
        self.assertEqual(len(SOURCES['pinned_commit']), 40)
    def test_wrong_sha_refuses(self):
        src=dict(SOURCES['sources'][0]);src['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'MISMATCH'):
            load_manifest(src)
if __name__=='__main__':unittest.main()
