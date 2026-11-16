"""AIOps-only cleanup must retain AAP, unrelated owners and external evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from test_decommission_guest_access import fixture, RETIRE

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_aiops_teardown', ROOT / 'src/aap_aiops_teardown.py')
helpers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helpers)


class ScopedRetirementTests(unittest.TestCase):
    def inputs(self):
        inputs = list(fixture())
        inputs[3]['zabbix'].update(hypervisor_machine_id=inputs[2]['hypervisor']['machine_id'], bridge='vmbr0')
        return inputs

    def test_paths_exclude_aap_but_retain_exact_three_roles(self):
        inputs = self.inputs()
        plan = helpers.resources(inputs[2], 'example.invalid', inputs[3])
        self.assertEqual({row['name'] for row in plan['domains']}, {'zabbix-v07', 'testserver1-v07', 'tra-v07'})
        self.assertNotIn('disk', plan)
        self.assertNotIn('authority', plan)
        self.assertEqual(plan['dns'], ['redhat.v07', 'zabbix.v07'])
        self.assertTrue(all('aap27' not in value for key in ('nginx', 'certificates', 'website_paths') for value in plan[key]))

    def test_full_native_guard_then_projection_preserves_aap_and_foreign_grants(self):
        inputs = self.inputs()
        full = RETIRE.guest_access_plan(*inputs)
        before = copy.deepcopy(inputs)
        plan = helpers.scoped_access(full, inputs[2], inputs[3])
        self.assertEqual(inputs, before)
        self.assertEqual(plan['identities'], [full['identities'][1]])
        self.assertEqual(plan['desired_policy']['guest_host_clients'], [inputs[0]['guest_host_clients'][0], inputs[0]['guest_host_clients'][2]])
        self.assertEqual(plan['desired_policy']['https_clients'], inputs[0]['https_clients'])
        self.assertEqual(len(plan['rich_rules_to_remove']), 1)
        self.assertNotIn('2222', plan['rich_rules_to_remove'][0])

    def test_foreign_hypervisor_or_base_address_cannot_be_projected(self):
        for field, value in [('hypervisor_machine_id', '9' * 32), ('address', '192.168.70.10')]:
            inputs = self.inputs()
            full = RETIRE.guest_access_plan(*inputs)
            inputs[3]['zabbix'][field] = value
            with self.subTest(field=field), self.assertRaises(helpers.keys.StoreError):
                helpers.scoped_access(full, inputs[2], inputs[3])

    def test_unproved_nic_cannot_be_selected_from_a_name(self):
        inputs = self.inputs()
        full = RETIRE.guest_access_plan(*inputs)
        full['identities'] = full['identities'][:1]
        with self.assertRaises(helpers.keys.StoreError):
            helpers.scoped_access(full, inputs[2], inputs[3])

    def test_scoped_network_removes_unnamed_owned_dhcp_preserving_aap_and_foreign_xml(self):
        before = ('<network><name>isolated</name><bridge name="vmbr0"/><ip><dhcp>'
                  '<host mac="52:54:00:12:34:56" ip="192.168.70.10" name="aap27-test-7"/>'
                  '<host mac="52:54:00:12:34:57" ip="192.168.70.20"/>'
                  '<host mac="52:54:00:12:34:58" ip="192.168.70.30" name="other"/>'
                  '</dhcp></ip></network>')
        root = ET.fromstring(before)
        full = {'before': {'isolated': {'persistent': before}}, 'reservations': [
            {'network': 'isolated', 'scope': 'persistent', 'kind': 'ip-dhcp-host', 'xml': ET.tostring(row, encoding='unicode')}
            for row in root.findall('./ip/dhcp/host')]}
        route = self.inputs()[2]
        plan = helpers.scoped_reservations(full, route, [{'bridge': 'vmbr0', 'ipv4': '192.168.70.20', 'mac': '52:54:00:12:34:57'}])
        self.assertEqual(len(plan['reservations']), 1)
        after = ET.fromstring(plan['after']['isolated']['persistent'])
        self.assertEqual([row.get('ip') for row in after.findall('./ip/dhcp/host')], ['192.168.70.10', '192.168.70.30'])

    def test_profile_and_runtime_are_removed_together_only_from_exact_preimage(self):
        capture = {'cac_import_metadata': {'project_id': 'aiops-selfhealing-demo'},
                   'aiops_instances': {'aap27-test-7': {'tra': {'uuid': 'fixture'}}, 'aap27-test-8': {'untouched': True}},
                   'shared_token': 'synthetic-canary', 'history': ['earlier']}
        runtime = {'schema_version': 1, 'instances': {'aap27-test-7': {'secret': 'selected'}, 'aap27-test-8': {'secret': 'other'}}}
        profile = copy.deepcopy(capture['aiops_instances']['aap27-test-7'])
        desired, next_runtime = helpers.documents_without_instance(capture, runtime, 'aap27-test-7', profile)
        self.assertEqual(desired['aiops_instances'], {'aap27-test-8': {'untouched': True}})
        self.assertEqual(next_runtime['instances'], {'aap27-test-8': {'secret': 'other'}})
        self.assertEqual(desired['shared_token'], capture['shared_token'])
        self.assertEqual(desired['history'], capture['history'])
        self.assertEqual(helpers.documents_without_instance(desired, next_runtime, 'aap27-test-7', profile), (desired, next_runtime))
        with self.assertRaises(helpers.keys.StoreError):
            helpers.documents_without_instance(capture, runtime, 'aap27-test-7', {'different': True})
        missing = copy.deepcopy(runtime)
        missing['instances'].pop('aap27-test-7')
        with self.assertRaises(helpers.keys.StoreError):
            helpers.documents_without_instance(capture, missing, 'aap27-test-7', profile)

    def test_active_or_unknown_workers_cannot_be_declared_quiescent(self):
        self.assertTrue(helpers.require_quiescent([], [{'is_enabled': False}], [{'status': 'stopped'}]))
        for jobs, activations, instances in [([{'status': 'running'}], [], []), ([], [{'is_enabled': True}], []),
                                              ([], [{'is_enabled': False}], [{'status': 'starting'}])]:
            with self.assertRaises(helpers.keys.StoreError):
                helpers.require_quiescent(jobs, activations, instances)


class AuthoritativeAbsenceTests(unittest.TestCase):
    def answer(self, status='NXDOMAIN'):
        return {'rc': 0, 'stdout': (';; ->>HEADER<<- opcode: QUERY, status: ' + status + ', id: 42\n'
            ';; flags: qr aa; QUERY: 1, ANSWER: 0, AUTHORITY: 1, ADDITIONAL: 1\n'
            ';; QUESTION SECTION:\n;redhat.v07.example.invalid. IN A\n'
            ';; AUTHORITY SECTION:\nexample.invalid. 600 IN SOA ns1.example.net. dns.example.net. 42 3600 600 86400 600\n'
            ';; SERVER: 192.0.2.53#53(192.0.2.53)\n')}

    def test_correct_zone_authoritative_nxdomain_or_nodata_proves_absence(self):
        for status in ('NXDOMAIN', 'NOERROR'):
            self.assertTrue(helpers.authority_absent(self.answer(status), 'redhat.v07.example.invalid', 'example.invalid', '192.0.2.53'))

    def test_wrong_question_zone_server_flags_alias_referral_or_malformed_response_refused(self):
        original = self.answer()
        for old, new in [('flags: qr aa;', 'flags: qr;'), ('flags: qr aa;', 'flags: qr aa rd;'),
                         ('flags: qr aa;', 'flags: qr aa tc;'), ('status: NXDOMAIN', 'status: SERVFAIL'),
                         (';redhat.v07.example.invalid. IN A', ';other.v07.example.invalid. IN A'),
                         ('example.invalid. 600 IN SOA', 'invalid. 600 IN SOA'),
                         (' IN SOA ', ' IN NS '), ('192.0.2.53#53', '192.0.2.54#53'),
                         ('ANSWER: 0', 'ANSWER: 1'), ('AUTHORITY: 1', 'AUTHORITY: 2'),
                         (' 42 3600 600 86400 600', ' 42 3600 600 86400')]:
            bad = copy.deepcopy(original)
            bad['stdout'] = bad['stdout'].replace(old, new)
            with self.subTest(change=new):
                self.assertFalse(helpers.authority_absent(bad, 'redhat.v07.example.invalid', 'example.invalid', '192.0.2.53'))

    def test_every_authority_must_prove_absence_in_same_complete_round(self):
        endpoints = [{'address': '192.0.2.53'}, {'address': '192.0.2.54'}]
        good = self.answer()
        second = self.answer()
        second['stdout'] = second['stdout'].replace('192.0.2.53#53', '192.0.2.54#53')
        observations = [dict(good, item=endpoints[0]), dict(second, item=endpoints[1])]
        self.assertTrue(helpers.authority_absent_round(observations, endpoints, 'redhat.v07.example.invalid', 'example.invalid')['ready'])
        observations[1]['stdout'] = observations[1]['stdout'].replace('flags: qr aa;', 'flags: qr;')
        self.assertFalse(helpers.authority_absent_round(observations, endpoints, 'redhat.v07.example.invalid', 'example.invalid')['ready'])


class WorkloadPublicationTests(unittest.TestCase):
    def test_existing_registry_and_api_transition_remove_only_three_guests(self):
        from test_instance_keys import retirement_fixture, application_capture, FakeRetirementSource
        context, _, main, shared, hactar, allocation = retirement_fixture()
        app = application_capture(context)
        app.update(aiops_website_dns_zone='example.invalid', aiops_zabbix_source_image={'sha256': 'c' * 64})
        resource = app['aiops_instances'][context['route']['vm_name']]['zabbix']
        resource.update(instance_name=context['route']['vm_name'], instance_number=7, source_sha256='c' * 64,
                        ip=resource['address'], public_hostname='zabbix.v07.example.invalid',
                        certificate='zabbix.v07.example.invalid', nginx_file='/etc/nginx/conf.d/demo-zabbix-v07.conf',
                        auth_file='/etc/nginx/demo-zabbix-v07.htpasswd')
        native = next(row for row in shared['host_inventory_configuration']['hosts'] if row['name'] == 'zabbix-v07')
        native['variables']['vm_resource'] = copy.deepcopy(resource)
        before = copy.deepcopy((main, shared, hactar, allocation))
        client = FakeRetirementSource(main, shared, hactar)
        plan = helpers.publication_context(main, shared, allocation, client,
            context['route']['vm_name'], context['route']['hypervisor'], app)
        self.assertEqual({row['role'] for row in plan['guests']}, {'zabbix', 'testserver1', 'tra'})
        aap_client = context['previous_policy']['guest_host_clients'][0]
        self.assertIn(aap_client, plan['desired_policy']['guest_host_clients'])
        self.assertIn(context['previous_policy']['https_clients'][0], plan['desired_policy']['https_clients'])
        desired = {kind: helpers.keys.retire_inventory_capture(value, plan, kind)
                   for kind, value in [('autodeploy', main), ('shared', shared), ('hactar', hactar)]}
        names = [row['name'] for row in desired['shared']['host_inventory_configuration']['hosts']]
        for name in ['zabbix-v07', 'testserver1-v07', 'tra-v07']:
            self.assertNotIn(name, names)
        self.assertIn(context['route']['vm_name'], names)
        self.assertIn('other-v08', names)
        self.assertEqual(desired['autodeploy']['aap_instance_api_credentials'], main['aap_instance_api_credentials'])
        self.assertEqual((main, shared, hactar, allocation), before)
        operations = helpers.keys.source_retirement_operations(client, desired['shared'], desired['autodeploy'], desired['hactar'], plan)
        aap_ids = {row['id'] for row in client.hosts.values() if row['name'] == context['route']['vm_name']}
        self.assertTrue(all(path not in {'hosts/%d/' % value for value in aap_ids} for method, path, body in operations if method == 'DELETE'))
        for method, path, body in operations:
            client.request(method, path, body)
        repeated = helpers.publication_context(desired['autodeploy'], desired['shared'], allocation, client,
            context['route']['vm_name'], context['route']['hypervisor'], app, helpers.publication_transition(plan))
        self.assertEqual(repeated['desired_policy'], plan['desired_policy'])
        self.assertFalse(helpers.keys.source_retirement_operations(client, desired['shared'], desired['autodeploy'], desired['hactar'], repeated))


class RuntimeCredentialTests(unittest.TestCase):
    def test_selected_overrides_win_and_missing_selected_never_falls_back(self):
        capture = {'aiops_instances': {'selected': {}}, 'demo_website_dns_api_token': 'shared-website',
                   'demo_zabbix_dns_api_token': 'shared-zabbix'}
        runtime = {'schema_version': 1, 'instances': {'selected': {'demo_website_dns_api_token': 'selected-website',
                                                                'demo_zabbix_dns_api_token': 'selected-zabbix'}}}
        self.assertEqual(helpers.selected_dns_tokens(capture, runtime, 'selected')['demo_website_dns_api_token'], 'selected-website')
        for broken in ({'schema_version': 1, 'instances': {}}, {'schema_version': 1, 'instances': {'selected': {}}}):
            with self.assertRaises(helpers.keys.StoreError):
                helpers.selected_dns_tokens(capture, broken, 'selected')

    def test_fully_retired_namespace_allows_shared_read_only_absence_token(self):
        capture = {'aiops_instances': {}, 'demo_website_dns_api_token': 'shared-website',
                   'demo_zabbix_dns_api_token': 'shared-zabbix'}
        self.assertEqual(helpers.selected_dns_tokens(capture, {'schema_version': 1, 'instances': {}}, 'selected')['demo_zabbix_dns_api_token'], 'shared-zabbix')
        with self.assertRaises(helpers.keys.StoreError):
            helpers.selected_dns_tokens(capture, {'schema_version': 1, 'instances': {'selected': {}}}, 'selected')


class SubscriptionNativeArtifactTests(unittest.TestCase):
    def test_exact_finished_native_job_artifact_only_and_no_fabricated_success(self):
        from copy import deepcopy
        profile = {'tra': {'vm_name': 'tra-v07', 'uuid': '11111111-2222-4333-8444-555555555555', 'machine_id': 'b'*32}}
        template = {'id': 12, 'project': 13, 'inventory': 14}
        proof = dict(instance_name='aap27-test-7',guest_name='tra-v07',uuid=profile['tra']['uuid'],machine_id='b'*32,
                     registration_absent=True,consumer_certificate_absent=True,consumer_uuid='99999999-2222-4333-8444-555555555555',
                     target_job_id='23',target_job_template_id='12',target_project_revision='a'*40)
        job = dict(id=23,job_template=12,project=13,inventory=14,playbook='playbooks/retire_tra_subscription.yml',limit='tra',
                   status='successful',failed=False,event_processing_finished=True,scm_revision='a'*40,
                   artifacts={'aap_aiops_subscription_absence':proof})
        project={'id':13,'scm_revision':'a'*40}
        result=helpers.verified_subscription_artifact(job,template,project,profile,'aap27-test-7',23,31,'c'*40)
        self.assertEqual(result['target_job']['id'],23)
        import yaml
        recorded=helpers.record_subscription_absence({'aiops_instances':{'aap27-test-7':profile}},'aap27-test-7',result,31,'c'*40)
        restored=helpers.codec.load_repository_yaml(yaml.safe_dump(recorded))
        self.assertTrue(helpers.subscription_absence_valid(restored['aiops_instances']['aap27-test-7'],'aap27-test-7'))
        wrong=deepcopy(restored['aiops_instances']['aap27-test-7']);wrong['teardown']['subscription_absence']['target_job']['id']=True
        self.assertFalse(helpers.subscription_absence_valid(wrong,'aap27-test-7'))
        wrong=deepcopy(restored['aiops_instances']['aap27-test-7']);wrong['teardown']['foreign_state']={}
        self.assertFalse(helpers.subscription_absence_valid(wrong,'aap27-test-7'))
        cases=[]
        for field,value in [('job_template',99),('inventory',99),('project',99),('limit','all'),('status','running'),
                            ('event_processing_finished',False),('scm_revision','d'*40),('playbook','foreign.yml')]:
            wrong=deepcopy(job);wrong[field]=value;cases.append(wrong)
        for field,value in [('uuid','99999999-2222-4333-8444-555555555555'),('machine_id','d'*32),
                            ('target_job_id','22'),('target_job_template_id','13'),('registration_absent',False),('consumer_certificate_absent',False)]:
            wrong=deepcopy(job);wrong['artifacts']['aap_aiops_subscription_absence'][field]=value;cases.append(wrong)
        for wrong in cases:
            with self.assertRaises(helpers.keys.StoreError):
                helpers.verified_subscription_artifact(wrong,template,project,profile,'aap27-test-7',23,31,'c'*40)


class PublicationOwnershipTests(unittest.TestCase):
    def test_foreign_certificate_docroot_auth_include_or_rate_zone_is_preserved(self):
        plan={'scope':'aiops','version':'v07','nginx':['/etc/nginx/conf.d/site.conf','/etc/nginx/conf.d/monitor.conf'],
              'certificates':['site.example.invalid','monitor.example.invalid'],
              'website_paths':['/var/www/owned-site','/etc/nginx/owned-auth','/etc/nginx/owned-rate.conf']}
        own='# configuration file /etc/nginx/conf.d/site.conf:\n# Managed by the AIOps website playbook for site.example.invalid.\nserver_name site.example.invalid;\n'
        self.assertTrue(helpers.publications_owned(own,plan))
        for content in ['/etc/letsencrypt/live/site.example.invalid/cert.pem','/var/www/owned-site',
                        '/etc/nginx/owned-auth','/etc/nginx/owned-rate.conf','limit_req zone=redhat_v07_panic;']:
            with self.subTest(reference=content),self.assertRaises(helpers.keys.StoreError):
                helpers.publications_owned(own+'# configuration file /etc/nginx/conf.d/foreign.conf:\n'+content+'\n',plan)
        with self.assertRaises(helpers.keys.StoreError):
            helpers.publications_owned(own.replace('server_name site.example.invalid;', 'server_name site.example.invalid other.example.invalid;'),plan)
