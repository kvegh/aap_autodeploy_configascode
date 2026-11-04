"""Keep approved native firewalld grants in encrypted and source declarations."""
from copy import deepcopy
import json
import unittest

from ansible.utils.unsafe_proxy import AnsibleUnsafeText
from test_aap_hypervisor_access import fixture, access
from test_instance_keys import keys, FakeRetirementSource


def prepared(mode):
    expected, _, main, shared, hactar, allocation = fixture()
    route, primary = expected['route'], expected['primary']
    desired = access.desired_policy(route, primary, expected['declared_policy'], mode)
    record = allocation['aap_vm_allocation']['reservations']['selected-request']
    context = keys.management_access_context(main, record, route['vm_name'], route, desired, mode)
    destination, port = (route['hypervisor']['public_ip'], 443) if mode == 'installation' else (
        route['hypervisor']['address'], route['hypervisor']['port'])
    rule = ('rule family="ipv4" priority="0" source address="%s/32" destination address="%s/32" '
            'port port="%s" protocol="tcp" accept' % (primary['address'], destination, port))
    return context, rule, main, shared, hactar, allocation


def selected_row(configuration, kind):
    if kind == 'autodeploy': return configuration['autodeploy_configuration']['inventories'][0]
    if kind == 'shared': return configuration['host_inventory_configuration']['hosts'][0]
    return configuration['controller_hosts_hactar_recovery'][0]


class NativeRulePersistenceTests(unittest.TestCase):
    def test_both_modes_append_only_exact_current_rule_in_all_three_captures(self):
        for mode in ('installation', 'management'):
            context, rule, main, shared, hactar, _ = prepared(mode)
            tokens_before = deepcopy(main['aap_instance_api_credentials'])
            for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
                with self.subTest(mode=mode, kind=kind):
                    row = selected_row(configuration, kind)
                    values = keys.inventory_variables(row)
                    # Force absence while retaining every unrelated native entry and literal wrapper.
                    old_rules = [entry for entry in values.get('firewall_additional_zone_rules', [])
                                 if entry.get('zone') != 'libvirt' or entry.get('rule') != rule]
                    values['firewall_additional_zone_rules'] = deepcopy(old_rules)
                    values['preserved_literal'] = '{{ unchanged_literal }}'
                    keys.set_inventory_variables(row, values)
                    original = deepcopy(configuration)
                    updated = keys.management_inventory_capture(configuration, context, kind)
                    changed = keys.inventory_variables(selected_row(updated, kind))
                    self.assertEqual(configuration, original)
                    self.assertEqual(changed['firewall_additional_zone_rules'], old_rules + [{'zone': 'libvirt', 'rule': rule}])
                    self.assertEqual(changed['preserved_literal'], values['preserved_literal'])
                    self.assertEqual(changed['isolation_policy'], context['desired_policy'])
                    self.assertEqual(changed['hactar_isolation_policy'], context['desired_policy'])
                    self.assertIsInstance(selected_row(updated, kind)['variables'], AnsibleUnsafeText)
                    self.assertEqual(keys.management_inventory_capture(updated, context, kind), updated)
                    if kind == 'autodeploy':
                        self.assertEqual(updated['aap_instance_api_credentials'], tokens_before)
                        self.assertEqual(updated['autodeploy_configuration']['credentials'], original['autodeploy_configuration']['credentials'])
                        self.assertEqual(changed['aap_hypervisor_pin'], context['route']['hypervisor'])

    def test_two_source_alias_updates_get_exact_rule_then_second_pass_is_noop(self):
        for mode in ('installation', 'management'):
            with self.subTest(mode=mode):
                context, rule, main, shared, hactar, _ = prepared(mode)
                # Both captured aliases refer to one actual source host, as in production.
                hrow = hactar['controller_hosts_hactar_recovery'][0]
                hrow['name'] = shared['host_inventory_configuration']['hosts'][0]['name']
                hrow['inventory'] = 'Shared'
                client = FakeRetirementSource(main, shared, hactar)
                client.hosts = {key: row for key, row in client.hosts.items() if row['inventory'] != 2}
                for row in [client.inventories[3], client.hosts[10]]:
                    values = keys.inventory_variables(row)
                    values['firewall_additional_zone_rules'] = [entry for entry in values.get('firewall_additional_zone_rules', [])
                        if entry.get('zone') != 'libvirt' or entry.get('rule') != rule]
                    row['variables'] = json.dumps(values)
                updated = {kind: keys.management_inventory_capture(cfg, context, kind)
                           for cfg, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar'))}
                operations = keys.source_management_operations(client, updated['shared'], updated['autodeploy'], updated['hactar'], context)
                self.assertEqual(len(operations), 2)
                for method, path, body in operations:
                    self.assertEqual(method, 'PATCH')
                    values = json.loads(body['variables'])
                    self.assertEqual(values['firewall_additional_zone_rules'].count({'zone': 'libvirt', 'rule': rule}), 1)
                    client.request(method, path, body)
                self.assertEqual(keys.source_management_operations(client, updated['shared'], updated['autodeploy'], updated['hactar'], context), [])

    def test_conflicting_or_duplicate_selected_native_declarations_fail_without_mutation(self):
        context, rule, *_ = prepared('installation')
        for rules in ([{'zone': 'libvirt', 'rule': rule, 'state': 'disabled'}],
                      [{'zone': 'libvirt', 'rule': rule.replace(' accept', ' drop')}],
                      [{'zone': 'libvirt', 'rule': rule.replace('priority="0"', 'priority="1"')}],
                      [{'zone': 'libvirt', 'rule': rule}, {'zone': 'libvirt', 'rule': rule}]):
            values = {'firewall_additional_zone_rules': deepcopy(rules), 'keep': '{{ unchanged }}'}
            original = deepcopy(values)
            with self.subTest(rules=rules), self.assertRaises(keys.StoreError):
                keys.source_management_variables(values, context)
            self.assertEqual(values, original)
        foreign = {'zone': 'public', 'rule': rule.replace(' accept', ' drop')}
        values = {'firewall_additional_zone_rules': [foreign]}
        updated = keys.source_management_variables(values, context)
        self.assertEqual(updated['firewall_additional_zone_rules'], [foreign, {'zone': 'libvirt', 'rule': rule}])
        self.assertEqual(keys.source_management_variables(updated, context), updated)


if __name__ == '__main__': unittest.main()
