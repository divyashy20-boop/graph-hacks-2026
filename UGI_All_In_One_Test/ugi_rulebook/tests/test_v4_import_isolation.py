"""Regression: v3 stale module import and missing source_id crashed all 49 live cases."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from ugi_rulebook.preflight import (
    PreflightError, assert_runtime_module_origins, validate_prepared_sources,
)

ROOT=Path(__file__).resolve().parents[2]
VALID={
    'projectA':{'source':{'name':'projectA'},'source_id':'sourceA'},
    'projectB':{'source':{'name':'projectB'},'source_id':'sourceB'},
}

class RuntimePackageIsolationTests(unittest.TestCase):
    def test_current_modules_resolve_exact_packaged_path(self):
        got=assert_runtime_module_origins(ROOT)
        self.assertTrue(got['ugi_real_track1.real_suite'].startswith(str(ROOT)))

    def test_stale_cwd_shadow_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            pkg=tmp/'ugi_real_track1';pkg.mkdir()
            (pkg/'__init__.py').write_text('')
            (pkg/'real_suite.py').write_text('def prepare(*args): return {}\n')
            program='from ugi_rulebook.preflight import assert_runtime_module_origins; assert_runtime_module_origins('+repr(str(ROOT))+')'
            env=dict(os.environ,PYTHONPATH=str(ROOT)+os.pathsep+str(tmp))
            bad=subprocess.run([sys.executable,'-c',program],cwd=tmp,env=env,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('STALE_MODULE_IMPORTED',bad.stderr)
            good=subprocess.run([sys.executable,'-c',program],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)

    def test_valid_ingestion_provenance_accepted(self):
        self.assertTrue(validate_prepared_sources(VALID))

    def test_v2_prepared_rows_without_source_id_rejected_preflight(self):
        old={'projectA':{'source':{'name':'projectA'},'services':['backend','db']}}
        with self.assertRaisesRegex(PreflightError,'SOURCE_ID_MISSING'):
            validate_prepared_sources(old)

    def test_empty_or_null_source_ids_rejected(self):
        for bad in ('',None,123,'  '):
            with self.subTest(source_id=bad):
                with self.assertRaisesRegex(PreflightError,'SOURCE_ID_MISSING'):
                    validate_prepared_sources({'projectA':{'source':{'name':'projectA'},'source_id':bad}})

    def test_provenance_cannot_be_reused_across_datasets(self):
        bad={**VALID,'projectC':{'source':{'name':'projectC'},'source_id':'sourceA'}}
        with self.assertRaisesRegex(PreflightError,'DUPLICATED'):
            validate_prepared_sources(bad)

    def test_prepared_dataset_name_mismatch_rejected(self):
        with self.assertRaisesRegex(PreflightError,'SOURCE_SCOPE_MISMATCH'):
            validate_prepared_sources({'projectA':{'source':{'name':'projectB'},'source_id':'a'}})

    def test_unsupported_metadata_structure_rejected(self):
        with self.assertRaises(PreflightError):validate_prepared_sources({'p':None})

    def test_windows_runner_always_uses_package_workdir(self):
        script=(ROOT/'START_ALL_TESTS_WINDOWS.ps1').read_text()
        self.assertIn('$testCwd="/tmp/ugi_aio_pkg_${runId}"',script)
        self.assertNotIn('-w /tmp $cid python',script)
        self.assertIn("'-w',$testCwd,$cid,'python'",script)
        self.assertIn('ugi_rulebook.preflight --expected-root $testCwd',script)
        self.assertNotIn("'/tmp/ugi_all_in_one_pkg:/tmp/ugi_mcp_sdk:/tmp:/app'",script)

    def test_one_query_runner_uses_package_workdir(self):
        script=(ROOT/'RUN_ONE_QUERY_WINDOWS.ps1').read_text()
        self.assertIn('-w $runtime.package_dir $cid python',script)
        self.assertNotIn('-w /tmp $cid python',script)

if __name__=='__main__':unittest.main()
