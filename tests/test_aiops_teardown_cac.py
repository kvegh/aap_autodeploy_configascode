"""A fresh capture append must preserve concurrent native publisher state."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import aap_aiops_teardown_cac as helper


class TeardownCaCTests(unittest.TestCase):
    def fixture(self):
        base = {'name': helper.BASE, 'playbook': 'destroy-test-aap.yml', 'credentials': ['one','two','three','four','five','six'],
                'inventory': 'Saved native hypervisor', 'project': 'Saved Source', 'limit': 'saved-target',
                'allow_simultaneous': False, 'job_type': 'run', 'ask_inventory_on_launch': False,
                'ask_limit_on_launch': False, 'ask_credential_on_launch': False, 'ask_execution_environment_on_launch': False,
                'extra_vars': {'aap_hactar_source_revision': '{{ aap_autodeploy_hactar_source_revision }}'}}
        return {'autodeploy_configuration': {'job_templates': [base], 'hosts': [{'name': 'new-concurrent-owner'}]},
                'aap_instance_api_credentials': {'latest': {'token_id': 42}}, 'history': ['retained']}

    def test_only_append_and_native_access_reuse_idempotent(self):
        before = self.fixture()
        result = helper.candidate(before)
        row = result['autodeploy_configuration']['job_templates'].pop()
        self.assertEqual(result, before)
        self.assertEqual(row['credentials'], before['autodeploy_configuration']['job_templates'][0]['credentials'])
        self.assertEqual(row['survey_spec']['spec'][1]['default'], 'preview')
        once = helper.candidate(before)
        self.assertEqual(helper.candidate(once), once)

    def test_conflicting_definition_or_weakened_native_launch_guard_refused(self):
        before = self.fixture()
        wrong = helper.candidate(before)
        wrong['autodeploy_configuration']['job_templates'][-1]['limit'] = 'all'
        with self.assertRaises(ValueError):
            helper.candidate(wrong)
        for field in ('ask_inventory_on_launch', 'ask_limit_on_launch', 'ask_credential_on_launch', 'allow_simultaneous'):
            candidate = deepcopy(before)
            candidate['autodeploy_configuration']['job_templates'][0][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                helper.candidate(candidate)


class SourceTeardownLoggingTests(unittest.TestCase):
    def test_all_owned_tasks_and_blocks_preserve_temporary_visible_logging(self):
        import yaml
        root=Path(__file__).resolve().parents[1]
        def check(rows):
            for row in rows:
                self.assertIs(row.get('no_log'),False,row.get('name'))
                for key in ('block','rescue','always','pre_tasks','tasks'):
                    if key in row:check(row[key])
        for path in [root/'teardown-aiops-workload.yml',*sorted((root/'tasks').glob('aiops-teardown-*.yml'))]:
            with self.subTest(path=path.name):check(yaml.safe_load(path.read_text()))
