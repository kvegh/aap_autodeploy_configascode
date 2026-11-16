"""Native-ID preimages, delivery shutdown, foreign relationships and delete races."""
import copy
import importlib.util
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('api_aiops_teardown', ROOT / 'src/aap_aiops_teardown.py')
lifecycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lifecycle)


class Target:
    def __init__(self):
        self.calls = []
        self.kinds = {path: [] for kind, path in lifecycle.TARGET_KINDS}
        self.creds = {9: [4]}
        self.labels = {9: [6]}
        self.active = []
        self.schedules = []
        self.workflows = []
        self.sources = []
        self.workflow_templates = []
        self.workflow_credentials = {}
        self.application_tokens = []
        org = {'id': 1, 'name': 'Default'}
        self.definitions = {
            'controller_projects': [{'name': 'AIOps Source', 'organization': 'Default', 'scm_type': 'git', 'scm_url': 'https://git.example.invalid/aiops.git', 'scm_branch': 'main'}],
            'controller_inventories': [{'name': 'AIOps Inventory', 'organization': 'Default'}],
            'controller_execution_environments': [{'name': 'AIOps EE', 'organization': 'Default', 'image': 'registry.example.invalid/ee@sha256:' + 'a' * 64}],
            'controller_credentials': [{'name': 'AIOps Vault', 'organization': 'Default', 'credential_type': 'Vault'}],
            'aap_applications': [{'name': 'AIOps EDA', 'organization': 'Default', 'client_type': 'confidential', 'authorization_grant_type': 'password'}],
            'controller_labels': [{'name': 'aiops_selfhealing', 'organization': 'Default'}],
            'controller_hosts': [{'name': 'tra', 'inventory': 'AIOps Inventory', 'variables': {'ansible_host': '192.0.2.44'}}],
            'controller_templates': [{'name': 'AIOps Owned Job', 'organization': 'Default', 'project': 'AIOps Source', 'inventory': 'AIOps Inventory', 'playbook': 'playbooks/owned.yml'}],
            'eda_projects': [{'name': 'AIOps EDA Source', 'organization': 'Default', 'url': 'https://git.example.invalid/aiops.git'}],
            'eda_decision_environments': [{'name': 'AIOps DE', 'organization': 'Default', 'image_url': 'registry.example.invalid/de@sha256:' + 'b' * 64}],
            'eda_credentials': [{'name': 'AIOps Basic', 'organization': 'Default', 'credential_type': 'Basic Event Stream'}],
            'eda_event_streams': [{'name': 'AIOps Events', 'organization': 'Default'}],
            'eda_rulebook_activations': [{'name': 'AIOps Receiver', 'organization': 'Default', 'project': 'AIOps EDA Source', 'decision_environment': 'AIOps DE', 'rulebook': 'owned.yml'}],
        }
        ids = {'controller_projects': 1, 'controller_inventories': 2, 'controller_execution_environments': 3,
               'controller_credentials': 4, 'aap_applications': 5, 'controller_labels': 6, 'controller_hosts': 7,
               'controller_templates': 9, 'eda_projects': 11, 'eda_decision_environments': 12, 'eda_credentials': 13,
               'eda_event_streams': 14, 'eda_rulebook_activations': 15}
        for kind, path in lifecycle.TARGET_KINDS:
            expected = copy.deepcopy(self.definitions[kind][0])
            expected.update(id=ids[kind], organization=org)
            if 'project' in expected:
                expected['project'] = {'id': 11, 'name': 'AIOps EDA Source'} if kind.startswith('eda_') else 1
            if 'inventory' in expected:
                expected['inventory'] = 2
            if 'decision_environment' in expected:
                expected['decision_environment'] = {'id': 12, 'name': 'AIOps DE'}
            if 'credential_type' in expected:
                expected['credential_type'] = {'id': 21, 'name': expected['credential_type']}
            if kind == 'controller_templates':
                expected['summary_fields'] = {'project': {'name': 'AIOps Source'}, 'inventory': {'name': 'AIOps Inventory'}}
                expected['execution_environment'] = 3
            if kind == 'controller_hosts':
                expected['summary_fields'] = {'inventory': {'name': 'AIOps Inventory'}}
            if kind == 'controller_projects':
                expected['current_job'] = None
            if kind == 'eda_rulebook_activations':
                expected.update(is_enabled=True, current_job_id=None, rulebook_name=expected.pop('rulebook'),
                                eda_credentials=[{'id': 13}], event_streams=[{'id': 14}])
            if kind == 'eda_event_streams':
                expected['eda_credential'] = {'id': 13}
            self.kinds[path] = [expected]

    def rows(self, path):
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        if parsed.path == '/api/controller/v2/jobs/':
            return copy.deepcopy(self.active)
        if parsed.path == '/api/controller/v2/workflow_job_templates/':
            return copy.deepcopy(self.workflow_templates)
        if parsed.path.startswith('/api/controller/v2/workflow_job_') and parsed.path.endswith('/credentials/'):
            return copy.deepcopy(self.workflow_credentials.get(int(parsed.path.strip('/').split('/')[-2]), []))
        if parsed.path.startswith('/api/gateway/v1/applications/') and parsed.path.endswith('/tokens/'):
            return copy.deepcopy(self.application_tokens)
        if parsed.path == '/api/controller/v2/workflow_job_template_nodes/':
            return copy.deepcopy(self.workflows)
        if parsed.path == '/api/controller/v2/inventory_sources/':
            return copy.deepcopy(self.sources)
        for suffix, mapping in [('credentials/', self.creds), ('labels/', self.labels)]:
            prefix = '/api/controller/v2/job_templates/'
            if parsed.path.startswith(prefix) and parsed.path.endswith('/' + suffix):
                identity = int(parsed.path[len(prefix):].split('/')[0])
                return [{'id': value, 'name': 'aiops_selfhealing' if suffix == 'labels/' else 'AIOps Vault'} for value in mapping.get(identity, [])]
        if parsed.path.endswith('/schedules/'):
            return copy.deepcopy(self.schedules)
        rows = copy.deepcopy(self.kinds.get(parsed.path, []))
        for field in ('id', 'name', 'inventory', 'project', 'execution_environment', 'credential'):
            if field in query:
                rows = [row for row in rows if str(row.get(field)) == query[field][0]]
        for field, mapping in [('credentials', self.creds), ('labels', self.labels)]:
            if field in query:
                rows = [row for row in rows if int(query[field][0]) in mapping.get(row['id'], [])]
        return rows

    def request(self, method, path, body=None):
        self.calls.append((method, path))
        for endpoint, values in self.kinds.items():
            if path.startswith(endpoint):
                remainder = path[len(endpoint):].strip('/').split('/')
                if not remainder[0].isdigit():
                    continue
                identity = int(remainder[0])
                matches = [row for row in values if row['id'] == identity]
                if not matches:
                    raise AssertionError('Unexpected absent native detail')
                row = matches[0]
                if method == 'GET':
                    return copy.deepcopy(row)
                if method == 'POST' and remainder[-1] == 'disable':
                    row['is_enabled'] = False
                    row['current_job_id'] = None
                    return {}
                if method == 'DELETE':
                    values.remove(row)
                    return {}
        raise AssertionError((method, path))


class TargetLifecycleTests(unittest.TestCase):
    def test_real_ids_dependency_order_and_verified_idempotent_absence(self):
        target = Target()
        plan = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        self.assertFalse(lifecycle.quiesce_target(target, plan)['quiescent'])
        self.assertFalse(any(method == 'POST' for method, path in target.calls))
        self.assertTrue(lifecycle.quiesce_target(target, plan, apply=True)['quiescent'])
        self.assertTrue(lifecycle.remove_target(target, plan))
        deletions = [path for method, path in target.calls if method == 'DELETE']
        self.assertEqual(deletions[0], '/api/eda/v1/activations/15/')
        self.assertLess(deletions.index('/api/controller/v2/job_templates/9/'), deletions.index('/api/controller/v2/credentials/4/'))
        repeated = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        self.assertEqual(repeated['operations'], [])
        self.assertFalse(lifecycle.remove_target(target, repeated))

    def test_foreign_controller_reference_stops_before_event_disable_or_delete(self):
        target = Target()
        target.kinds['/api/controller/v2/job_templates/'].append({'id': 90, 'name': 'Other tool', 'project': 1})
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        self.assertFalse(any(method in ('POST', 'DELETE') for method, path in target.calls))

    def test_foreign_eda_stream_keeps_shared_credentials(self):
        target = Target()
        target.kinds['/api/eda/v1/event-streams/'].append({'id': 90, 'name': 'Other stream', 'eda_credential': {'id': 13}})
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')

    def test_running_job_is_waited_for_never_cancelled(self):
        target = Target()
        plan = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        target.active = [{'id': 51, 'status': 'running'}]
        self.assertFalse(lifecycle.quiesce_target(target, plan, apply=True)['quiescent'])
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.remove_target(target, plan)
        self.assertFalse(any('cancel' in path for method, path in target.calls))

    def test_changed_native_ownership_refuses_delete(self):
        target = Target()
        plan = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        lifecycle.quiesce_target(target, plan, apply=True)
        target.kinds['/api/controller/v2/job_templates/'][0]['playbook'] = 'foreign.yml'
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.remove_target(target, plan)
        self.assertTrue(target.kinds['/api/controller/v2/job_templates/'])
        self.assertTrue(target.kinds['/api/controller/v2/inventories/'])

    def test_new_foreign_dependency_after_plan_is_not_cascaded(self):
        target = Target()
        plan = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        lifecycle.quiesce_target(target, plan, apply=True)
        target.kinds['/api/controller/v2/job_templates/'].append({'id': 90, 'name': 'Other tool', 'project': 1})
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.remove_target(target, plan)
        self.assertTrue(target.kinds['/api/controller/v2/projects/'])


class ForeignWorkflowTests(unittest.TestCase):
    def test_foreign_workflow_inventory_and_node_credential_refused_before_mutation(self):
        for node in (False, True):
            target = Target()
            if node:
                target.workflows = [{'id': 88, 'inventory': None}]
                target.workflow_credentials[88] = [{'id': 4}]
            else:
                target.workflow_templates = [{'id': 87, 'inventory': 2}]
            with self.assertRaises(lifecycle.keys.StoreError):
                lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
            self.assertFalse(any(method != 'GET' for method, path in target.calls))

    def test_foreign_workflow_appearing_after_plan_keeps_inventory(self):
        target = Target()
        plan = lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        lifecycle.quiesce_target(target, plan, apply=True)
        target.workflow_templates = [{'id': 87, 'inventory': 2}]
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.remove_target(target, plan)
        self.assertTrue(target.kinds['/api/controller/v2/inventories/'])

    def test_application_token_is_not_cascaded_without_ownership(self):
        target = Target()
        target.application_tokens = [{'id': 99}]
        with self.assertRaises(lifecycle.keys.StoreError):
            lifecycle.selected_target_plan(target, target.definitions, 'aiops_selfhealing')
        self.assertTrue(target.kinds['/api/gateway/v1/applications/'])


class TargetAccessTokenTests(unittest.TestCase):
    def fixture(self, receipted=True):
        target=Target();target.hostname='https://target.example.invalid'
        expected={'name':'Owned EDA Controller access','organization':'Default','description':'Owned native controller access',
                  'credential_type':'Red Hat Ansible Automation Platform',
                  'inputs':{'host':target.hostname+'/api/controller','oauth_token':'','verify_ssl':True}}
        target.definitions['eda_credentials'].append(expected)
        description=lifecycle.api_tokens.eda_token_description(expected,target.hostname,41,11)if receipted else expected['description']
        row=dict(expected,id=16,description=description,organization={'id':1,'name':'Default'},
                 credential_type={'id':22,'name':expected['credential_type']},inputs=dict(expected['inputs'],oauth_token='$encrypted$'))
        target.kinds['/api/eda/v1/eda-credentials/'].append(row)
        token={'id':41,'user':11,'scope':'write','application':None,'expires':None,'description':'CaC EDA Controller access: '+expected['name']}
        target.kinds['/api/gateway/v1/tokens/']=[token,dict(token,id=99,description='Other base API token')]
        return target,expected

    def test_receipt_is_retained_before_owner_delete_and_only_its_native_token_is_revoked(self):
        target,expected=self.fixture();plan=lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing')
        self.assertEqual(len(plan['access_tokens']),1)
        capture={'aiops_instances':{'selected':{'unrelated':'preserved'}},'other':'preserved'}
        retained=lifecycle.record_target_access(capture,'selected',plan)
        self.assertEqual(capture['aiops_instances']['selected'],{'unrelated':'preserved'})
        receipts=retained['aiops_instances']['selected']['teardown']['target_access_tokens']
        lifecycle.quiesce_target(target,plan,apply=True)
        self.assertTrue(lifecycle.revoke_target_access(target,plan,[99]))
        self.assertTrue(lifecycle.access_tokens_absent(target,plan))
        self.assertEqual([row['id']for row in target.kinds['/api/gateway/v1/tokens/']],[99])
        self.assertTrue(lifecycle.remove_target(target,plan))
        repeated=lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing',receipts)
        self.assertFalse(lifecycle.revoke_target_access(target,repeated,[99]))

    def test_native_owner_deleted_after_receipt_still_recovers_exact_token_custody(self):
        target,expected=self.fixture();plan=lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing')
        receipts=[row['receipt']for row in plan['access_tokens']]
        target.kinds['/api/eda/v1/eda-credentials/']=[row for row in target.kinds['/api/eda/v1/eda-credentials/']if row['id']!=16]
        recovered=lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing',receipts)
        self.assertTrue(lifecycle.revoke_target_access(target,recovered,[99]))
        self.assertEqual([row['id']for row in target.kinds['/api/gateway/v1/tokens/']],[99])

    def test_legacy_or_orphan_description_never_grants_deletion_ownership(self):
        target,expected=self.fixture(receipted=False)
        with self.assertRaises(lifecycle.keys.StoreError):lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing')
        target.kinds['/api/eda/v1/eda-credentials/']=[row for row in target.kinds['/api/eda/v1/eda-credentials/']if row['id']!=16]
        with self.assertRaises(lifecycle.keys.StoreError):lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing')
        self.assertFalse(any(method in('POST','DELETE')for method,path in target.calls))

    def test_base_access_foreign_token_or_changed_owner_is_never_revoked(self):
        for change in ('base','token','credential'):
            target,expected=self.fixture();plan=lifecycle.selected_target_plan(target,target.definitions,'aiops_selfhealing')
            if change=='token':target.kinds['/api/gateway/v1/tokens/'][0]['user']=99
            if change=='credential':target.kinds['/api/eda/v1/eda-credentials/'][1]['inputs']['host']='https://other.example.invalid/api/controller'
            with self.subTest(change=change),self.assertRaises((lifecycle.keys.StoreError,lifecycle.api_tokens.LifecycleError)):
                lifecycle.revoke_target_access(target,plan,[41]if change=='base'else[])
            self.assertFalse(any(method=='DELETE'for method,path in target.calls))


class OwnerReceiptCASPreimageTests(unittest.TestCase):
    def test_current_owner_must_match_preflight_before_any_receipt_publication(self):
        expected={'tra':{'vm_name':'tra-v07','uuid':'11111111-2222-4333-8444-555555555555','machine_id':'b'*32},
                  'event_stream_password':'synthetic'}
        plan={'access_tokens':[]}
        valid=copy.deepcopy(expected);valid['teardown']={'target_access_tokens':[]}
        self.assertTrue(lifecycle.owner_preimage_matches(valid,expected,'aap27-test-7',plan))
        cases=[]
        changed=copy.deepcopy(valid);changed['tra']['uuid']='99999999-2222-4333-8444-555555555555';cases.append(changed)
        changed=copy.deepcopy(valid);changed['event_stream_password']='another';cases.append(changed)
        changed=copy.deepcopy(valid);changed['teardown']['foreign_work']={};cases.append(changed)
        changed=copy.deepcopy(valid);changed['teardown']['subscription_absence']={};cases.append(changed)
        for changed in cases:
            with self.assertRaises(lifecycle.keys.StoreError):lifecycle.owner_preimage_matches(changed,expected,'aap27-test-7',plan)
        with self.assertRaises(lifecycle.keys.StoreError):lifecycle.owner_preimage_matches(expected,valid,'aap27-test-7',plan)
