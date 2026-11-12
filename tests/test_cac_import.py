"""Bound project selection, native API authentication and real Ansible rendering."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ansible.errors import AnsibleFilterError
from ansible.template import trust_as_template
from ansible.utils.unsafe_proxy import wrap_var
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cac_import', ROOT / 'filter_plugins/cac_import.py')
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)
VAULT_SPEC = importlib.util.spec_from_file_location('test_cac_yaml', ROOT / 'src/cac_yaml.py')
vault_yaml = importlib.util.module_from_spec(VAULT_SPEC)
VAULT_SPEC.loader.exec_module(vault_yaml)


def metadata(project='assistant-team'):
    return {'schema_version': 1, 'project_id': project, 'required_template_label': 'synthetic',
            'resource_variables': {'controller_templates': 'captured.templates'},
            'checks': {}, 'capabilities': {}}


def offline_capture_validation():
    """Retain real import validation while forbidding external fixture actions."""
    source = vault_yaml.load_repository_yaml((ROOT / 'deploy-cac-project.yml').read_text())[0]
    tasks = source['pre_tasks'][-1]['block']
    first = next(i for i, task in enumerate(tasks) if task['name'].startswith('Initialize the declared'))
    last = next(i for i, task in enumerate(tasks) if task['name'].startswith('Check the dedicated'))
    external_hooks = {'tasks/cac-orchestrator-ee.yml', 'tasks/cac-shared-execution-image.yml'}
    validation = []
    for original in tasks[first:last]:
        task = deepcopy(original)
        include = task.get('ansible.builtin.include_tasks')
        if include in external_hooks:
            continue  # Native API/build/SSH boundaries have their own synthetic tests.
        actions = set(task) & {'ansible.builtin.set_fact', 'ansible.builtin.assert',
                              'aap_cac_prepare_resources', 'ansible.builtin.include_tasks'}
        # Fail closed if future validation code adds a remote action or include.
        if len(actions) != 1 or any(key.startswith(('ansible.', 'aap_')) and key not in actions for key in task):
            raise AssertionError('The offline rendering fixture must not execute external actions.')
        if include:
            if include != 'tasks/cac-template-labels.yml':
                raise AssertionError('The offline rendering fixture has an unreviewed include.')
            label_tasks = vault_yaml.load_repository_yaml((ROOT / include).read_text())
            if not all('ansible.builtin.assert' in row for row in label_tasks):
                raise AssertionError('Template-label validation must remain assertions only in this fixture.')
            task['ansible.builtin.include_tasks'] = str(ROOT / include)
        task['no_log'] = True
        validation.append(task)
    return validation


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

    def test_all_reviewed_projects_derive_their_own_repository_and_file(self):
        for project in filters.PROJECT_IDS:
            result = filters.project_contract(project, 'https://git.example.invalid/example-owner')
            self.assertEqual(result['repository'], 'https://git.example.invalid/example-owner/' + project + '-secrets.git')
            self.assertEqual(result['configuration_file'], 'vaults/cac/' + project + '-cac-vault.yml')

    def test_rhel_contract_preserves_the_reviewed_repository_and_capture_case(self):
        result = filters.project_contract('RHEL-sniperpatching', 'https://git.example.invalid/example-owner')
        self.assertEqual(result['repository'], 'https://git.example.invalid/example-owner/RHEL-sniperpatching-secrets.git')
        self.assertEqual(result['configuration_file'], 'vaults/cac/RHEL-sniperpatching-cac-vault.yml')
        for project in ('rhel-sniperpatching', 'Rhel-sniperpatching', 'RHEL-sniperpatching/other'):
            with self.subTest(project=project), self.assertRaises(AnsibleFilterError):
                filters.project_contract(project, 'https://git.example.invalid/example-owner')

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
    def test_unsafe_launch_values_do_not_freeze_other_resources_or_literal_injectors(self):
        validation = offline_capture_validation()
        configuration = metadata('aiops-selfhealing-demo')
        configuration['resource_variables'] = {
            'controller_projects': 'captured.projects',
            'controller_credential_types': 'captured.types',
            'controller_execution_environments': 'captured.environments',
            'controller_templates': 'captured.templates',
            'controller_labels': 'captured.labels',
            'eda_event_streams': 'captured.streams',
            'eda_rulebook_activations': 'captured.activations',
        }
        configuration['checks'] = {'true_values': ['capture_reviewed'], 'resource_counts': {
            'controller_templates': 1, 'controller_labels': 1, 'controller_execution_environments': 2}}
        configuration['capabilities'] = {'eda_controller_access': {
            'credential_name': 'Example Controller', 'organization': trust_as_template('{{ example_organization }}'),
            'token_variable': 'example_persistent_token'}}
        with tempfile.TemporaryDirectory(prefix='cac-unsafe-resource-fixture-') as temporary:
            root = Path(temporary)
            for native in ('false', 'true'):
                output_file = root / ('result-' + native + '.json')
                variables = {
                    'aap_hostname': wrap_var('https://target-aap.example.invalid'),
                    'aap_token': wrap_var('synthetic-unsafe-api-token-canary'),
                    'aap_instance_key': wrap_var('example-aap'),
                    'runtime_value': 'synthetic-injector-evaluation-must-not-appear',
                    'capture_reviewed': True,
                    'cac_project_contract': {'project_id': 'aiops-selfhealing-demo'},
                    'aap_shared_execution_image': 'target-aap.example.invalid/ee-proj-aap-cac@sha256:' + '2' * 64,
                    'example_organization': 'Example', 'cac_import_metadata': configuration,
                    'captured': {
                        'projects': [{'name': 'Project', 'scm_url': trust_as_template('{{ aap_hostname }}/example.git')}],
                        'environments': [
                            {'name': 'Owned EE', 'image': trust_as_template('{{ aap_shared_execution_image }}')},
                            {'name': 'Foreign EE', 'image': 'foreign.example.invalid/custom:stable'}],
                        'templates': [{'name': 'Example job', 'organization': 'Example', 'labels': ['synthetic']}],
                        'labels': [{'name': 'synthetic', 'organization': 'Example'}],
                        'types': [{'name': 'Runtime credential', 'injectors': {
                            'env': {'EXAMPLE_RUNTIME_TOKEN': wrap_var('{{ runtime_value }}')}}}],
                        'streams': [{'name': 'Stream', 'organization_name': trust_as_template('{{ example_organization }}'),
                                     'credential_name': 'Stream authentication'}],
                        'activations': [{'event_streams': [{'event_stream': 'Stream', 'source_name': 'events'}]}],
                    },
                }
                retain = {'name': 'Retain only synthetic rendered values for checks', 'no_log': True,
                          'ansible.builtin.copy': {'dest': str(output_file), 'mode': '0600',
                              'content': trust_as_template("{{ {'url': cac_import_resources.controller_projects[0].scm_url, 'organization': cac_import_resources.eda_event_streams[0].organization, 'literal': cac_import_resources.controller_credential_types[0].injectors.env.EXAMPLE_RUNTIME_TOKEN, 'owned_image': cac_import_resources.controller_execution_environments[0].image, 'foreign_image': cac_import_resources.controller_execution_environments[1].image} | to_json }}")}}
                fixture = root / 'fixture.yml'
                # These reviewed fixture expressions represent repository code;
                # the injector represents runtime data and must remain literal.
                # VaultDumper intentionally preserves that distinction on 2.20.
                expected_literals = {('captured', 'types', 0, 'injectors', 'env', 'EXAMPLE_RUNTIME_TOKEN')}
                self.assertEqual(vault_yaml.literal_paths(variables), expected_literals)
                fixture.write_text(yaml.dump([{'hosts': 'localhost', 'connection': 'local',
                    'gather_facts': False, 'vars': variables, 'tasks': [*validation, retain]}],
                    Dumper=vault_yaml.VaultDumper, sort_keys=False))
                restored = vault_yaml.load_repository_yaml(fixture.read_text())[0]
                self.assertEqual(vault_yaml.literal_paths(restored['vars']), expected_literals)
                self.assertFalse(vault_yaml.literal_template(restored['tasks'][-1]['ansible.builtin.copy']['content']))
                environment = dict(os.environ, ANSIBLE_JINJA2_NATIVE=native,
                    ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                    ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'), ANSIBLE_NOCOLOR='1',
                    ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
                run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(fixture)],
                    cwd=ROOT, env=environment, text=True, capture_output=True, timeout=45)
                output = run.stdout + run.stderr
                self.assertNotIn('synthetic-unsafe-api-token-canary', output)
                self.assertNotIn('synthetic-injector-evaluation-must-not-appear', output)
                self.assertEqual(run.returncode, 0, output)
                result = json.loads(output_file.read_text())
                self.assertEqual(result, {'url': 'https://target-aap.example.invalid/example.git',
                    'organization': 'Example', 'literal': '{{ runtime_value }}',
                    'owned_image': variables['aap_shared_execution_image'],
                    'foreign_image': 'foreign.example.invalid/custom:stable'})

    def test_missing_instance_store_fails_clearly_before_any_api_call(self):
        with tempfile.TemporaryDirectory(prefix='cac-native-auth-fixture-') as temporary:
            directory = Path(temporary)
            fixture = directory / 'fixture.yml'
            fixture.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                               'gather_facts': False, 'tasks': [{
                                                   'ansible.builtin.include_tasks': str(ROOT / 'tasks/cac-api-auth.yml')}]}]))
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(('AAP_', 'TOWER_', 'CONTROLLER_'))}
            environment.update(ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'),
                               ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                               ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(directory / 'remote'),
                               AAP_PASSWORD='synthetic-auth-password-canary')
            run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(fixture)],
                                 cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30)
            output = run.stdout + run.stderr
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('Attach AAP API/MCP Auth Token Store', output)
            self.assertNotIn('synthetic-auth-password-canary', output)
            self.assertNotIn('TASK [Authenticate', output)

    @unittest.skipUnless(Path('/tmp/aap-cac-project-migration/candidate-plaintext').is_dir(),
                         'requires protected migration candidates; no production API is used')
    def test_all_reviewed_real_captures_render_and_validate_in_both_native_modes(self):
        password_file = os.environ.get('AAP_CAC_TEST_VAULT_PASSWORD_FILE')
        if not password_file:
            self.skipTest('Set AAP_CAC_TEST_VAULT_PASSWORD_FILE explicitly for protected candidate rendering.')
        self.assertTrue(Path(password_file).is_file(), 'The explicit protected-test Vault password file must exist.')
        validation = offline_capture_validation()
        candidate_root = Path('/tmp/aap-cac-project-migration/candidate-plaintext')
        with tempfile.TemporaryDirectory(prefix='cac-render-fixture-') as temporary:
            directory = Path(temporary)
            environment = dict(os.environ, ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'),
                               ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                               ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(directory / 'remote'))
            for native in ('false', 'true'):
                for project in sorted(filters.PROJECT_IDS):
                    capture = candidate_root / project / (project + '-cac-vault.yml')
                    variables = {'aap_hostname': 'https://test-aap.example.invalid',
                                 'aap_instance_key': wrap_var('synthetic-aap'),
                                 'aap_validate_certs': True, 'aap_token': 'synthetic-destination-token',
                                 'aap_username': '', 'aap_password': '',
                                 'aap_shared_execution_image': 'test-aap.example.invalid/ee-proj-aap-cac@sha256:' + '2' * 64,
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
                    fixture.write_text(yaml.dump(play, Dumper=vault_yaml.VaultDumper, sort_keys=False))
                    environment['ANSIBLE_JINJA2_NATIVE'] = native
                    run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                          '--vault-password-file', password_file, str(fixture)],
                                         cwd=ROOT, env=environment, text=True, capture_output=True, timeout=90)
                    self.assertEqual(run.returncode, 0, '%s/native=%s\n%s' % (project, native, run.stdout + run.stderr))


if __name__ == '__main__':
    unittest.main()
