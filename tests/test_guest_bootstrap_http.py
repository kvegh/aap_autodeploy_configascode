"""Keep temporary HTTP bootstrap exact, durable and distinct from full release."""
from copy import deepcopy
import unittest

from ansible.errors import AnsibleFilterError

from test_guest_release import fixture, keys
from test_guest_release_runtime import fixture as runtime_fixture, runtime
from test_aap_hypervisor_access import fixture as management_fixture
from test_decommission_guest_access import fixture as decommission_fixture


def prepared():
    guest, pin, main, shared, hactar, allocation = fixture(new=True)
    https = keys.guest_release_context(main, shared, guest, pin, access='bootstrap_https')
    captures = [keys.guest_release_inventory_capture(value, https, kind)
                for value, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar'))]
    return guest, pin, *captures, allocation


class GuestBootstrapHttpTests(unittest.TestCase):
    def test_http_requires_existing_complete_ownership_and_adds_no_other_permission(self):
        guest, pin, main, shared, *_ = fixture(new=True)
        with self.assertRaises(keys.StoreError):
            keys.guest_release_context(main, shared, guest, pin, access='bootstrap_http')
        guest, pin, main, shared, hactar, _ = prepared()
        context = keys.guest_release_context(main, shared, guest, pin, access='bootstrap_http')
        identity = {key: guest[field] for key, field in (('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))}
        expected = deepcopy(context['previous_policy'])
        expected['http_clients'] = [identity]
        self.assertEqual(context['desired_policy'], expected)
        self.assertIn(identity, expected['https_clients'])
        self.assertNotIn(identity, expected.get('released_clients', []))
        for original, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            updated = keys.guest_release_inventory_capture(original, context, kind)
            self.assertEqual(keys.guest_release_inventory_capture(updated, context, kind), updated)
            if kind == 'autodeploy':
                values = keys.inventory_variables(updated['autodeploy_configuration']['inventories'][0])
                self.assertEqual(values['aap_hypervisor_isolation_http_clients'], [identity])
                self.assertEqual(updated['aap_instance_api_credentials'], original['aap_instance_api_credentials'])
        for field in ('uuid', 'host_keys', 'machine_id'):
            changed = deepcopy(shared)
            row = next(row for row in changed['host_inventory_configuration']['hosts'] if row['name'] == guest['vm_name'])
            values = keys.inventory_variables(row)
            values['vm_resource'].pop(field)
            keys.set_inventory_variables(row, values)
            with self.subTest(field=field), self.assertRaises(keys.StoreError):
                keys.guest_release_context(main, changed, guest, pin, access='bootstrap_http')

    def test_missing_and_empty_http_input_omit_field_and_http_only_keeps_production_protection(self):
        guest, pin, *_ = prepared()
        identity = {key: guest[field] for key, field in (('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))}
        before = keys._routing.isolation_policy(pin)
        self.assertEqual(keys._routing.isolation_policy(pin, http_clients=[]), before)
        policy = keys._routing.isolation_policy(pin, protected_ipv4=['203.0.113.99'], http_clients=[identity])
        self.assertEqual(policy['http_clients'], [identity])
        self.assertNotIn('https_clients', policy)
        for bad in ([identity, identity], [dict(identity, ipv4='8.8.8.8')], [dict(identity, mac='00:00:00:00:00:00')]):
            with self.subTest(bad=bad), self.assertRaises(AnsibleFilterError):
                keys._routing.isolation_policy(pin, protected_ipv4=['203.0.113.99'], http_clients=bad)
        with self.assertRaises(AnsibleFilterError):
            keys._routing.isolation_policy(pin, http_clients=[identity])
        with self.assertRaises(AnsibleFilterError):
            keys._routing.isolation_policy(pin, [dict(identity, mac='52:54:00:00:00:98')], ['203.0.113.99'], http_clients=[identity])

    def test_runtime_uses_same_native_identity_checks_and_exact_http_only_rollback(self):
        request, state = runtime_fixture()
        request['mode'] = 'bootstrap_http'
        before = request['transition']['previous_policy']
        identity = deepcopy(before['https_clients'][0])
        request['transition']['desired_policy'] = dict(deepcopy(before), http_clients=[identity])
        self.assertTrue(runtime.plan(request, state)['changed'])
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        self.assertFalse(runtime.plan(request, state)['changed'])
        rollback = dict(request, operation='rollback')
        self.assertEqual(runtime.plan(rollback, state)['desired_policy'], before)
        for variant in ('release', 'other-client', 'uuid', 'protected', 'drift'):
            changed, observed = deepcopy(request), deepcopy(state)
            if variant == 'release': changed['transition']['desired_policy']['released_clients'] = [identity]
            elif variant == 'other-client': changed['transition']['desired_policy']['http_clients'].append(dict(identity, ipv4='192.168.10.8'))
            elif variant == 'uuid': changed['guest']['uuid'] = '99999999-2222-3333-4444-555555555555'
            elif variant == 'protected': changed['transition']['desired_policy']['protected_ipv4'] = []
            else: observed['policy']['https_clients'] = []
            with self.subTest(variant=variant), self.assertRaises(ValueError): runtime.plan(changed, observed)

    def test_other_release_and_management_operations_preserve_http(self):
        expected, _, main, shared, hactar, allocation = management_fixture()
        identity = deepcopy(expected['declared_policy']['https_clients'][0])
        for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            rows = (configuration['autodeploy_configuration']['inventories'] if kind == 'autodeploy' else
                    configuration['host_inventory_configuration']['hosts'] if kind == 'shared' else configuration['controller_hosts_hactar_recovery'])
            for row in rows:
                values = keys.inventory_variables(row)
                for alias in ('isolation_policy', 'hactar_isolation_policy'):
                    if alias in values: values[alias]['http_clients'] = [identity]
                if kind == 'autodeploy': values['aap_hypervisor_isolation_http_clients'] = [identity]
                keys.set_inventory_variables(row, values)
        context = keys.installation_access_context(main, shared, allocation, expected['route'], expected['primary'])
        self.assertEqual(context['desired_policy']['http_clients'], [identity])
        for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            updated = keys.installation_inventory_capture(configuration, context, kind)
            if kind == 'autodeploy':
                values = keys.inventory_variables(updated['autodeploy_configuration']['inventories'][0])
                self.assertEqual(values['aap_hypervisor_isolation_http_clients'], [identity])
        shared = keys.merge_inventory(shared, expected['route']['vm_name'], expected['route'],
                                      context['desired_policy'], expected['primary'])
        aap = {'kind': 'aap', 'route': expected['route'], 'primary': expected['primary'], 'guest_machine_id': 'a' * 32}
        final = keys.aap_release_context(main, shared, allocation, aap, expected['route']['hypervisor'])
        self.assertEqual(final['desired_policy']['http_clients'], [identity])
        guest, pin, main, shared, hactar, _ = prepared()
        bootstrap = keys.guest_release_context(main, shared, guest, pin, access='bootstrap_http')
        main = keys.guest_release_inventory_capture(main, bootstrap, 'autodeploy')
        shared = keys.guest_release_inventory_capture(shared, bootstrap, 'shared')
        release = keys.guest_release_context(main, shared, guest, pin)
        self.assertEqual(release['desired_policy']['http_clients'], bootstrap['desired_policy']['http_clients'])

    def test_aap_decommission_keeps_other_http_clients_and_their_production_exclusions(self):
        policy, retirement, route, resources, xmls, networks = decommission_fixture()
        selected, other = deepcopy(policy['https_clients'][:2])
        policy['http_clients'] = [selected, other]
        module = keys._routing
        normalized = module.isolation_policy(route['hypervisor'], policy.get('https_clients'), policy['protected_ipv4'],
            policy.get('guest_host_clients'), policy.get('released_clients'), policy['http_clients'])
        self.assertEqual(normalized, policy)
        from test_instance_keys import load
        retire = load('http_guest_decommission', 'filter_plugins/aap_decommission.py')
        planned = retire.guest_access_plan(policy, retirement, route, resources, xmls, networks)
        self.assertEqual(planned['desired_policy']['http_clients'], [other])
        self.assertEqual(planned['desired_policy']['protected_ipv4'], policy['protected_ipv4'])

    def test_retirement_removes_only_selected_http_and_keeps_other_http_protection(self):
        request, _ = runtime_fixture()
        guest = request['guest']
        identity = deepcopy(request['transition']['previous_policy']['https_clients'][0])
        other = dict(identity, ipv4='192.168.10.8', mac='52:54:00:00:00:08')
        policy = dict(deepcopy(request['transition']['previous_policy']), http_clients=[identity, other])
        expected = deepcopy(policy)
        expected.pop('https_clients')
        expected['http_clients'] = [other]
        self.assertEqual(keys.generic_retirement_policy(policy, guest), expected)
        self.assertEqual(runtime._retirement_policy(policy, guest), expected)
        with self.assertRaises(keys.StoreError):
            keys.verify_remaining_guest_grants(expected, {'missing_roles': ['tra'], 'policy_owners': []})


if __name__ == '__main__': unittest.main()
