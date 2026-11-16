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


class TargetHelperCaCTests(unittest.TestCase):
    def fixture(self):
        return {'controller_templates_aiops_demo':[{'name':'Deploy Linux MCP Server','job_type':'run','limit':'tra',
            'inventory':'Existing owned AIOps inventory','project':'Existing public AIOps project','credentials':['Machine','Vault'],
            'ask_inventory_on_launch':False,'ask_limit_on_launch':False,'ask_credential_on_launch':False,
            'ask_execution_environment_on_launch':False}], 'aiops_instances':{'newly-published':{'retained':True}},
            'aiops_runtime_settings_vault':'unchanged encrypted runtime'}

    def test_fresh_native_owner_and_runtime_survive_only_one_fixed_helper_append(self):
        before=self.fixture();after=helper.target_candidate(before);row=after['controller_templates_aiops_demo'].pop()
        self.assertEqual(after,before)
        self.assertEqual(row['limit'],'tra');self.assertEqual(row['timeout'],600)
        self.assertEqual(row['credentials'],before['controller_templates_aiops_demo'][0]['credentials'])
        self.assertFalse(row['ask_variables_on_launch'])
        once=helper.target_candidate(before);self.assertEqual(helper.target_candidate(once),once)

    def test_changed_or_unfixed_target_access_refuses_without_overwriting(self):
        before=self.fixture();before['controller_templates_aiops_demo'][0]['ask_limit_on_launch']=True
        with self.assertRaises(ValueError):helper.target_candidate(before)
        before=self.fixture();after=helper.target_candidate(before);after['controller_templates_aiops_demo'][-1]['timeout']=7200
        with self.assertRaises(ValueError):helper.target_candidate(after)


class ReviewedTemplateCountTests(unittest.TestCase):
    def cases(self):
        return [(TeardownCaCTests().fixture(), helper.candidate, 'autodeploy_configuration.job_templates'),
                (TargetHelperCaCTests().fixture(), helper.target_candidate, 'controller_templates_aiops_demo')]

    def reviewed(self, capture, path, count=1):
        capture['cac_import_metadata'] = {'resource_variables': {'controller_templates': path},
            'checks': {'resource_counts': {'controller_templates': count, 'controller_credentials': 6}},
            'other_metadata': {'preserve': True}}
        return capture

    def test_declared_count_advances_only_with_the_new_row_and_then_stays_unchanged(self):
        for original, transform, path in self.cases():
            before = self.reviewed(original, path)
            with self.subTest(scope=path):
                after = transform(before)
                self.assertEqual(after['cac_import_metadata']['checks']['resource_counts']['controller_templates'], 2)
                self.assertTrue(helper._typed_equal(transform(after), after))
                inverse = deepcopy(after)
                rows = inverse
                for field in path.split('.'): rows = rows[field]
                rows.pop()
                inverse['cac_import_metadata']['checks']['resource_counts']['controller_templates'] = 1
                self.assertTrue(helper._typed_equal(inverse, before))

    def test_stale_boolean_text_float_and_wrong_list_counts_refuse_before_any_append(self):
        for original, transform, path in self.cases():
            for bad in (True, False, 0, 2, -1, '1', 1.0):
                before = self.reviewed(deepcopy(original), path, bad); retained = deepcopy(before)
                with self.subTest(scope=path, count=bad), self.assertRaises(ValueError): transform(before)
                self.assertTrue(helper._typed_equal(before, retained))
            before = self.reviewed(deepcopy(original), 'wrong.resource.list')
            with self.assertRaises(ValueError): transform(before)
            after = transform(self.reviewed(deepcopy(original), path))
            after['cac_import_metadata']['checks']['resource_counts']['controller_templates'] = 1
            with self.assertRaises(ValueError): transform(after)

    def test_absent_declaration_is_not_introduced(self):
        for original, transform, path in self.cases():
            original['cac_import_metadata'] = {'checks': {'resource_counts': {}}}
            with self.subTest(scope=path):
                result = transform(original)
                self.assertEqual(result['cac_import_metadata'], original['cac_import_metadata'])

    def test_actual_codec_loaded_integer_count_and_literal_tags_survive_the_append(self):
        import yaml
        for original, transform, path in self.cases():
            before = self.reviewed(original, path)
            before['literal_input'] = '{{ fixture_canary_must_remain_literal }}'
            loaded = helper.codec.load_repository_yaml(yaml.dump(before, Dumper=helper.codec.VaultDumper, sort_keys=False))
            count = loaded['cac_import_metadata']['checks']['resource_counts']['controller_templates']
            self.assertIsInstance(count, int); self.assertNotIsInstance(count, bool)
            with self.subTest(scope=path):
                after = transform(loaded)
                restored = helper.codec.load_repository_yaml(yaml.dump(after, Dumper=helper.codec.VaultDumper, sort_keys=False))
                self.assertTrue(helper._typed_equal(restored, transform(restored)))
                inverse = deepcopy(restored); rows = inverse
                for field in path.split('.'): rows = rows[field]
                rows.pop(); inverse['cac_import_metadata']['checks']['resource_counts']['controller_templates'] = count
                self.assertTrue(helper._typed_equal(inverse, loaded))
                self.assertEqual(helper.codec.literal_paths(inverse), helper.codec.literal_paths(loaded))
