"""Regression: Docker cp root-owned old temp files prevented v4 from starting."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
RUNNER=(ROOT/'START_ALL_TESTS_WINDOWS.ps1').read_text()
ONE=(ROOT/'RUN_ONE_QUERY_WINDOWS.ps1').read_text()

class UniqueRunPathsTests(unittest.TestCase):
    def test_uuid_package_path_per_run(self):
        self.assertIn("$runId=[guid]::NewGuid().ToString('N').Substring(0,12)",RUNNER)
        self.assertIn('$testCwd="/tmp/ugi_aio_pkg_${runId}"',RUNNER)
    def test_uuid_hotfix_and_outputs(self):
        self.assertIn('$hotfixDir="/tmp/ugi_aio_engine_${runId}"',RUNNER)
        self.assertIn('$liveReport="/tmp/ugi_aio_result_${runId}.json"',RUNNER)
        self.assertIn('$patchReceipt="/tmp/ugi_aio_patch_${runId}.json"',RUNNER)
    def test_cannot_remove_old_test_paths(self):
        self.assertNotRegex(RUNNER,r'(?m)^\s*(?:docker exec|\& docker).*\brm\s+-rf\b')
        self.assertNotIn("rm -rf /tmp/ugi_all_in_one_pkg",RUNNER)
        self.assertNotIn("rm -rf /tmp/ugi_all_hotfix",RUNNER)
    def test_all_python_invocations_use_unique_dir(self):
        self.assertIn('$testCwd/$folder',RUNNER)
        self.assertIn('$testCwd/ugi_agent_fix/tests',RUNNER)
        self.assertIn('-w $testCwd',RUNNER)
        self.assertIn("'-w',$testCwd",RUNNER)
        self.assertIn('ugi_rulebook.preflight --expected-root $testCwd',RUNNER)
    def test_runner_saves_exact_runtime_locations(self):
        for label in ('container_id=$cid','package_dir=$testCwd','pythonpath=$patched','live_report=$liveReport'):
            self.assertIn(label,RUNNER)
        self.assertIn("'runtime_paths.json'",RUNNER)
    def test_one_query_no_stale_hardcoded_paths(self):
        self.assertNotIn('PYTHONPATH=/tmp/ugi_all_hotfix:',ONE)
        self.assertIn('runtime_paths.json',ONE)
        self.assertIn('-w $runtime.package_dir',ONE)
        self.assertIn('--report $runtime.live_report',ONE)
        self.assertIn('container_id -ne $cid',ONE)
    def test_one_query_fail_closed_for_untrusted_paths(self):
        self.assertIn('Untrusted package path',ONE)
        self.assertIn('Untrusted hotfix path',ONE)
        self.assertIn('Untrusted Python import path',ONE)
    def test_no_write_actions_in_runner(self):
        self.assertNotIn('docker compose down',RUNNER)
        self.assertNotIn('docker volume rm',RUNNER)
        self.assertNotIn('git reset',RUNNER)
        self.assertNotIn('git clean',RUNNER)
