"""Bound project selection, native API authentication and real Ansible rendering."""

from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ansible.errors import AnsibleFilterError
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cac_import', ROOT / 'filter_plugins/cac_import.py')
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)


def metadata(project='assistant-team'):
    return {'schema_version': 1, 'project_id': project, 'required_template_label': 'synthetic',
            'resource_variables': {'controller_templates': 'captured.templates'},
            'checks': {}, 'capabilities': {}}


class ImportContractTests(unittest.TestCase):
    def test_unreviewed_missing_placeholder_or_executable_configuration_is_rejected(self):
        configuration = metadata()
        configuration['checks'] = {'true_values': ['ready'], 'required_secret_lists': ['required'],
                                   'empty_lists': ['review_items']}
        configuration['resource_variables']['controller_schedules'] = 'schedules'
        complete = {'ready': True, 'required': ['synthetic_password'], 'synthetic_password': 'synthetic-password',
                    'review_items': [], 'captured': {'templates': []}, 'schedules': []}
        self.assertTrue(filters.validate_checks(configuration, complete))
        for overrides in ({'ready': False}, {'ready': 'true'}, {'synthetic_password': ''},
                          {'synthetic_password': '$encrypted$'}, {'synthetic_password': 'CHANGEME'},
                          {'required': ['missing_password']}, {'review_items': ['not reviewed']}):
            with self.subTest(overrides=overrides), self.assertRaises(AnsibleFilterError):
                filters.validate_checks(configuration, dict(complete, **overrides))
        with self.assertRaises(AnsibleFilterError):
            filters.resources_for_import(configuration, dict(complete, schedules=[{'name': 'Do not install'}]))

    def test_all_five_projects_derive_their_own_repository_and_file(self):
        for project in filters.PROJECT_IDS:
            result = filters.project_contract(project, 'https://git.example.invalid/example-owner')
            self.assertEqual(result['repository'], 'https://git.example.invalid/example-owner/' + project + '-secrets.git')
            self.assertEqual(result['configuration_file'], 'vaults/cac/' + project + '-cac-vault.yml')

    def test_unknown_ids_traversal_and_repository_override_shapes_fail(self):
        for project in ('', '../assistant-team', 'assistant-team/other', 'unknown', 123):
            with self.subTest(project=project), self.assertRaises(AnsibleFilterError):
                filters.project_contract(project, 'https://git.example.invalid/example-owner')
        for namespace in ('http://git.example.invalid/owner', 'https://token@git.example.invalid/owner',
                          'https://git.example.invalid/a/b', 'https://git.example.invalid/../owner',
                          'https://git.example.invalid/owner?override=true', 'https://git.example.invalid/owner/'):
            with self.subTest(namespace=namespace), self.assertRaises(AnsibleFilterError):
                filters.project_contract('assistant-team', namespace)

    def test_metadata_is_data_only_and_cannot_choose_roles_or_importer_variables(self):
        original = metadata()
        filters.import_metadata(original, 'assistant-team')
        for mutate in (
                lambda x: x.update(project_id='automation-orchestrator'),
                lambda x: x.update(task_file='../other.yml'),
                lambda x: x['resource_variables'].update(controller_settings='settings'),
                lambda x: x['resource_variables'].update(controller_templates='aap_password'),
                lambda x: x['resource_variables'].update(controller_templates="lookup('env', 'TOKEN')"),
                lambda x: x['capabilities'].update(arbitrary_role={'path': 'tasks/other.yml'})):
            bad = deepcopy(original)
            mutate(bad)
            with self.assertRaises(AnsibleFilterError):
                filters.import_metadata(bad, 'assistant-team')

    def test_capture_cannot_override_importer_facts_or_role_dispatch_controls(self):
        filters.validate_capture_roots({'cac_import_metadata': metadata(), 'cac_workflow': {}})
        for name in (*filters.FORBIDDEN_ROOTS, 'ansible_connection',
                     'controller_configuration_dispatcher_roles', 'gateway_users_secure_logging'):
            with self.subTest(name=name), self.assertRaises(AnsibleFilterError):
                filters.validate_capture_roots({'cac_import_metadata': metadata(), name: 'replacement'})

    def test_only_mapped_resources_are_imported_and_launches_are_refused(self):
        configuration = metadata()
        context = {'captured': {'templates': [{'name': 'Example', 'extra_vars': {'nested': '{{ runtime_input }}'}}]},
                   'controller_templates_ambient': [{'name': 'Must never import'}]}
        result = filters.resources_for_import(configuration, context)
        self.assertEqual(result['controller_templates'], context['captured']['templates'])
        self.assertEqual(result['controller_credentials'], [])
        configuration['resource_variables']['controller_launch_jobs'] = 'launches'
        context['launches'] = [{'job_template': 'Never launch'}]
        with self.assertRaises(AnsibleFilterError):
            filters.resources_for_import(configuration, context)

    def test_native_bearer_or_basic_must_match_selected_inventory_fqdn_and_tls(self):
        host = {'ansible_fqdn': 'test-aap.example.invalid', 'hypervisor_host': 'example-hypervisor'}
        bearer = {'hostname': 'https://test-aap.example.invalid', 'token': 'synthetic-token',
                  'username': '', 'password': '', 'validate_certs': 'true'}
        self.assertEqual(filters.api_target(host, bearer)['token'], 'synthetic-token')
        basic = dict(bearer, token='', username='synthetic-user', password='synthetic-password')
        self.assertEqual(filters.api_target(host, basic)['username'], 'synthetic-user')
        for update in ({'hostname': 'https://source-aap.example.invalid'}, {'validate_certs': False},
                       {'token': ''}, {'username': 'ambiguous-user'}, {'hostname': 'http://test-aap.example.invalid'},
                       {'hostname': 'https://test-aap.example.invalid/api/'}):
            with self.subTest(update=update), self.assertRaises(AnsibleFilterError):
                filters.api_target(host, dict(bearer, **update))

    def test_activation_and_snapshot_validation_rejects_unsafe_inputs(self):
        config = metadata('aiops-selfhealing-demo')
        config['capabilities'] = {'eda_controller_access': {'organization': 'Example'}}
        resources = {name: [] for name in filters.RESOURCE_VARIABLES}
        resources['eda_event_streams'] = [{'name': 'Stream', 'organization': 'Example', 'credential_name': 'Event auth'}]
        resources['eda_rulebook_activations'] = [{'event_streams': [{'event_stream': 'Stream', 'source_index': 0}]}]
        self.assertTrue(filters.validate_resources(resources, config))
        resources['eda_rulebook_activations'][0]['event_streams'][0]['source_name'] = 'Both is unsafe'
        with self.assertRaises(AnsibleFilterError):
            filters.validate_resources(resources, config)


class AnsibleCaptureRenderingTests(unittest.TestCase):
    def test_missing_native_destination_credential_fails_clearly_before_any_api_call(self):
        with tempfile.TemporaryDirectory(prefix='cac-native-auth-fixture-') as temporary:
            directory = Path(temporary)
            fixture = directory / 'fixture.yml'
            fixture.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                               'gather_facts': False, 'tasks': [{
                                                   'ansible.builtin.include_tasks': str(ROOT / 'tasks/cac-api-auth.yml')}]}]))
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(('AAP_', 'TOWER_', 'CONTROLLER_'))}
            environment.update(ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'),
                               ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(directory / 'remote'),
                               AAP_PASSWORD='synthetic-auth-password-canary')
            run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(fixture)],
                                 cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30)
            output = run.stdout + run.stderr
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('Select a native Red Hat Ansible Automation Platform credential', output)
            self.assertNotIn('synthetic-auth-password-canary', output)
            self.assertNotIn('TASK [Authenticate', output)

    @unittest.skipUnless(Path('/tmp/aap-cac-project-migration/candidate-plaintext').is_dir(),
                         'requires protected migration candidates; no production API is used')
    def test_all_five_real_captures_render_and_validate_in_both_native_modes(self):
        source = yaml.safe_load((ROOT / 'deploy-cac-project.yml').read_text())[0]
        tasks = source['pre_tasks'][-1]['block']
        first = next(i for i, task in enumerate(tasks) if task['name'].startswith('Initialize the declared'))
        last = next(i for i, task in enumerate(tasks) if task['name'].startswith('Check the dedicated'))
        validation = deepcopy(tasks[first:last])
        for task in validation:
            if task.get('ansible.builtin.include_tasks'):
                task['ansible.builtin.include_tasks'] = str(ROOT / task['ansible.builtin.include_tasks'])
            task['no_log'] = True
        candidate_root = Path('/tmp/aap-cac-project-migration/candidate-plaintext')
        with tempfile.TemporaryDirectory(prefix='cac-render-fixture-') as temporary:
            directory = Path(temporary)
            environment = dict(os.environ, ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'),
                               ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(directory / 'remote'))
            for native in ('false', 'true'):
                for project in sorted(filters.PROJECT_IDS):
                    capture = candidate_root / project / (project + '-cac-vault.yml')
                    variables = {'aap_hostname': 'https://test-aap.example.invalid',
                                 'aap_validate_certs': True, 'aap_token': 'synthetic-destination-token',
                                 'aap_username': '', 'aap_password': '',
                                 'cac_project_contract': {'project_id': project},
                                 'windows_disconnected_ad_target_ca': 'synthetic-prepared-public-ca',
                                 'windows_disconnected_ad_target_known_hosts': 'synthetic-prepared-public-host-key'}
                    play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                             'vars': variables,
                             'vars_files': [str(ROOT / 'myvars'), str(ROOT / 'vars/main.yml')],
                             'tasks': [{'name': 'Load protected candidate without printing its content',
                                        'ansible.builtin.include_vars': {'file': str(capture)}, 'no_log': True},
                                       *validation]}]
                    fixture = directory / 'fixture.yml'
                    fixture.write_text(yaml.safe_dump(play, sort_keys=False))
                    environment['ANSIBLE_JINJA2_NATIVE'] = native
                    run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                          '--vault-password-file', str(ROOT.parents[2] / 'vpf'), str(fixture)],
                                         cwd=ROOT, env=environment, text=True, capture_output=True, timeout=90)
                    self.assertEqual(run.returncode, 0, '%s/native=%s\n%s' % (project, native, run.stdout + run.stderr))


if __name__ == '__main__':
    unittest.main()
