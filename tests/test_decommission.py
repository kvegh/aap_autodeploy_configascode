"""Bound teardown to one reservation and preserve legacy route compatibility."""
import copy
import importlib.util
from pathlib import Path
import unittest
from ansible.errors import AnsibleFilterError

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'filter_plugins' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

retire = load('aap_decommission')
routing = load('aap_instance_route')

class DecommissionTests(unittest.TestCase):
    def test_numbered_public_names_share_the_reserved_number(self):
        self.assertEqual(routing.instance_public_name('aap27-test-7', 'example.invalid'), 'aap27.v07.example.invalid')
        self.assertEqual(routing.instance_public_name('aap27-test-123', 'example.invalid'), 'aap27.v123.example.invalid')
        for name in ('aap27-test-0', 'production', '../aap27-test-7'):
            with self.assertRaises(AnsibleFilterError):
                routing.instance_public_name(name, 'example.invalid')

    def test_legacy_and_new_routes_retire_only_their_same_version_resources(self):
        for hostname in ('aap27-test-7.example.invalid', 'aap27.v07.example.invalid'):
            result = retire.resources({'vm_name': 'aap27-test-7', 'aap_hostname': 'https://' + hostname},
                                      'example.invalid', '/opt/vms')
            self.assertEqual(result['dns'], [hostname.removesuffix('.example.invalid'), 'redhat.v07', 'zabbix.v07'])
            self.assertEqual(result['disk'], '/opt/vms/aap27-test-7.disk.qcow2')
            self.assertNotIn('/etc/nginx/conf.d/default.conf', result['nginx'])
        for route, directory in (({'vm_name':'production'}, '/opt/vms'),
                                  ({'vm_name':'aap27-test-7', 'aap_hostname':'https://foreign.invalid'}, '/opt/vms'),
                                  ({'vm_name':'aap27-test-7', 'aap_hostname':'https://aap27.v07.example.invalid'}, '/opt')):
            with self.assertRaises(AnsibleFilterError):
                retire.resources(route, 'example.invalid', directory)

    def test_extra_or_foreign_disks_refuse_domain_teardown(self):
        expected = retire.resources({'vm_name':'aap27-test-7', 'aap_hostname':'https://aap27.v07.example.invalid'},
                                    'example.invalid', '/opt/vms')
        disk = '<disk device="disk"><source file="/opt/vms/aap27-test-7.disk.qcow2"/></disk>'
        xml = '<domain><name>aap27-test-7</name><devices>' + disk + '</devices></domain>'
        self.assertTrue(retire.domain_matches(xml, expected))
        self.assertTrue(retire.domain_matches(xml.replace('<source file=', '<source index="1" file='), expected))
        self.assertFalse(retire.domain_matches(xml.replace('</devices>', disk + '</devices>'), expected))
        self.assertFalse(retire.domain_matches(xml.replace('aap27-test-7.disk', 'production.disk'), expected))
        self.assertFalse(retire.domain_matches(xml.replace('<name>aap27-test-7', '<name>production'), expected))

    def test_zone_scan_finds_orphaned_roles_without_matching_another_version(self):
        selected = retire.resources({'vm_name':'aap27-test-7','aap_hostname':'https://aap27.v07.example.invalid'}, 'example.invalid', '/opt/vms')
        records = [{'name':name,'type':'A','data':'192.0.2.10','ttl':600} for name in ('aap27.v07','redhat.v07','zabbix.v07','forgotten.v07','production','other.v070')]
        plan = retire.dns_plan(records, selected, '192.0.2.10', 'example.invalid')
        self.assertEqual({row['name'] for row in plan}, {'aap27.v07','redhat.v07','zabbix.v07','forgotten.v07'})
        records[3]['data']='198.51.100.10'
        with self.assertRaises(AnsibleFilterError):
            retire.dns_plan(records, selected, '192.0.2.10', 'example.invalid')

    def test_same_number_is_required_in_the_canonical_route(self):
        test = __import__('test_aap_name_allocation')
        fixture = test.RoutingTests()
        # Reuse the routing test's complete synthetic pin rather than weaken validation.
        route = fixture.route()
        route['aap_hostname'] = 'https://aap27.v15.example.invalid'
        self.assertEqual(routing.instance_route(route), route)
        route['aap_hostname'] = 'https://aap27.v16.example.invalid'
        with self.assertRaises(AnsibleFilterError):
            routing.instance_route(route)
