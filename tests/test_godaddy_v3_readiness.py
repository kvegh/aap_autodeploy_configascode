"""Prove authoritative-first ordering with native Ansible and deterministic DNS transport."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault('ANSIBLE_LOCAL_TEMP', '/tmp/aap-v3-ready-unit-local')
from ansible.errors import AnsibleFilterError
import yaml
import test_godaddy_v3 as v3

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v3_ready_filters', ROOT / 'filter_plugins/godaddy_v3.py')
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)
LEAF = 'appliance.v24-test2.example.invalid'
NAMES = ['ns1.example.invalid', 'ns2.example.invalid']
IPS = ['192.0.2.53', '192.0.2.54']
EXPECTED = '192.0.2.10'


def response(question=LEAF, kind='A', data=None, status='NOERROR', flags='qr aa', server=IPS[0], records=None):
    if records is None:
        records = [(question, kind, EXPECTED if data is None else data)] if status == 'NOERROR' else []
    return {'rc': 0, 'stdout': '\n'.join([
        ';; ->>HEADER<<- opcode: QUERY, status: ' + status + ', id: 11',
        ';; flags: ' + flags + '; QUERY: 1, ANSWER: ' + str(len(records)) + ', AUTHORITY: 0, ADDITIONAL: 0',
        ';; QUESTION SECTION:', ';' + question + '. IN ' + kind, '', ';; ANSWER SECTION:',
        *[name + '. 600 IN ' + rtype + ' ' + value for name, rtype, value in records],
        '', ';; SERVER: ' + server + '#53(' + server + ') (UDP)', ''])}


class ParserTests(unittest.TestCase):
    def test_exact_response_requires_real_AA_question_status_and_direct_owned_A(self):
        good = response()
        self.assertEqual(filters.godaddy_v3_dns_response(good, LEAF, 'A', True, IPS[0]), [EXPECTED])
        referral = response(flags='qr', records=[])
        referral['stdout'] = referral['stdout'].replace('AUTHORITY: 0', 'AUTHORITY: 1').replace(
            ';; SERVER:', ';; AUTHORITY SECTION:\nexample.invalid. 600 IN NS ns1.example.invalid.\n;; SERVER:')
        invalid = [response(status='NXDOMAIN'), response(flags='qr'), response(flags='qr aa tc'),
                   referral,
                   response(flags='qr aa rd'), response(question='other.example.invalid'),
                   response(server=IPS[1]), response(records=[(LEAF, 'CNAME', 'alias.example.invalid')]),
                   response(records=[('other.example.invalid', 'A', EXPECTED)]),
                   response(records=[]), {'rc': 9, 'stdout': ''}, {'rc': False, 'stdout': good['stdout']},
                   {'rc': 0, 'stdout': good['stdout'].replace('ANSWER: 1', 'ANSWER: 2')},
                   {'rc': 0, 'stdout': good['stdout'].replace('; QUERY: 1', '; QUERY: 2')},
                   {'rc': 0, 'stdout': 'malformed'}, {'rc': 0, 'stdout': good['stdout'] * 2}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_dns_response(value, LEAF, 'A', True, IPS[0])

    def test_public_apex_NS_must_match_provider_and_all_NS_addresses_are_retained(self):
        records = [v3.record(str(i), '@', name, kind='NS') for i, name in enumerate(NAMES)]
        ns = response('example.invalid', 'NS', flags='qr rd ra', server='8.8.8.8',
                      records=[('example.invalid', 'NS', name) for name in NAMES])
        self.assertEqual(filters.godaddy_v3_dns_nameservers(records, ns, 'example.invalid'), NAMES)
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_nameservers(records[:1], ns, 'example.invalid')
        resolved = [dict(response(name, 'A', data=ip, flags='qr rd ra', server='8.8.8.8'), item=name)
                    for name, ip in zip(NAMES, IPS)]
        self.assertEqual(filters.godaddy_v3_dns_endpoints(resolved, NAMES),
                         [{'nameserver': n, 'address': i} for n, i in zip(NAMES, IPS)])
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_endpoints(resolved[:1], NAMES)

    def test_round_requires_all_authorities_and_rejects_wrong_IP_or_incomplete_observations(self):
        endpoints = [{'nameserver': n, 'address': i} for n, i in zip(NAMES, IPS)]
        good = [dict(response(server=ip), item=endpoint) for endpoint, ip in zip(endpoints, IPS)]
        self.assertTrue(filters.godaddy_v3_dns_authority_round(good, endpoints, LEAF, EXPECTED)['ready'])
        for bad in [response(server=IPS[1], status='NXDOMAIN'), response(server=IPS[1], data='192.0.2.99'),
                    response(server=IPS[1], flags='qr'), response(server=IPS[1], question='other.example.invalid')]:
            changed = copy.deepcopy(good)
            changed[1] = dict(bad, item=endpoints[1])
            self.assertFalse(filters.godaddy_v3_dns_authority_round(changed, endpoints, LEAF, EXPECTED)['ready'])
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_authority_round(good[:1], endpoints, LEAF, EXPECTED)


DIG_STUB = r'''import sys,os,json
from pathlib import Path
p=Path(os.environ['FIXTURE_AUTHORITY_STATE']);s=json.loads(p.read_text());args=sys.argv[1:]
server=next(x[1:]for x in args if x.startswith('@'));name=next(x for x in args if x.endswith('.')and not x.startswith('@')).rstrip('.');kind=args[args.index(name+'.')+1]
s['calls'].append({'server':server,'name':name,'kind':kind,'norecurse':'+norecurse'in args})
flags='qr rd ra';status='NOERROR';rows=[];question=name
names=['ns1.example.invalid','ns2.example.invalid'];ips=['192.0.2.53','192.0.2.54'];leaf='appliance.v24-test2.example.invalid'
if server=='8.8.8.8'and name=='example.invalid'and kind=='NS':
 rows=[('example.invalid','NS',n)for n in names]
 if s.get('mismatch'):rows=rows[:1]
elif server=='8.8.8.8'and name in names and kind=='A':rows=[(name,'A',ips[names.index(name)])]
elif name==leaf and kind=='A'and server in ips:
 assert '+norecurse'in args
 flags='qr aa';s['counts'][server]=s['counts'].get(server,0)+1
 ok=s['counts'][server]>=s['ready_after'].get(server,1)
 if not ok:status='NXDOMAIN'
 else:rows=[(leaf,'A','192.0.2.10')]
 s['latest'][server]=ok
elif server=='8.8.8.8'and name==leaf and kind=='A':
 s['premature_recursive']=not all(s['latest'].get(ip,False)for ip in ips)
 p.write_text(json.dumps(s));print('192.0.2.10');raise SystemExit(0)
else:raise SystemExit(74)
p.write_text(json.dumps(s))
print(';; ->>HEADER<<- opcode: QUERY, status: '+status+', id: 11')
print(';; flags: '+flags+'; QUERY: 1, ANSWER: '+str(len(rows))+', AUTHORITY: 0, ADDITIONAL: 0')
print(';; QUESTION SECTION:');print(';'+question+'. IN '+kind);print('');print(';; ANSWER SECTION:')
for owner,typ,value in rows:print(owner+'. 600 IN '+typ+' '+value)
print('');print(';; SERVER: '+server+'#53('+server+') (UDP)')
'''


class NativeReadinessTests(unittest.TestCase):
    setUpClass = classmethod(v3.NativeTaskTests.setUpClass.__func__)
    tearDownClass = classmethod(v3.NativeTaskTests.tearDownClass.__func__)
    setUp = v3.NativeTaskTests.setUp
    run_tasks = v3.NativeTaskTests.run_tasks
    assert_ok = v3.NativeTaskTests.assert_ok

    def run_readiness(self, ready_after=None, mismatch=False, check=False, **overrides):
        self.state['records'] = [v3.record(str(i), '@', n, kind='NS') for i, n in enumerate(NAMES)]
        with tempfile.TemporaryDirectory(prefix='aap-authority-native-') as folder:
            folder = Path(folder)
            executable = folder / 'dig'
            executable.write_text('#!' + sys.executable + '\n' + DIG_STUB)
            executable.chmod(0o700)
            state = folder / 'state.json'
            state.write_text(json.dumps({'calls': [], 'counts': {}, 'latest': {}, 'mismatch': mismatch,
                                         'ready_after': ready_after or {IPS[0]: 1, IPS[1]: 2}}))
            final = next(t for t in yaml.safe_load((ROOT / '02-infra-config.yml').read_text())[0]['tasks']
                         if t['name'] == 'Wait for DNS propagation')
            tasks = [{'ansible.builtin.include_tasks': str(ROOT / 'tasks/aap-instance-dns-ready.yml')}, final]
            values = {'aap_hostname': 'https://' + LEAF, 'aap_test_subdomain': 'appliance.v24-test2',
                      'aap_dns_authority_max_rounds': 4, 'aap_dns_authority_poll_delay': 0,
                      'aap_dns_authority_timeout': 60,
                      'aap_instance_dns_readback': {'status': 200, 'json': v3.page([v3.record()])}}
            values['aap_instance_dns_readback']['json']['items'][0]['name'] = 'appliance.v24-test2'
            values.update(overrides)
            with mock.patch.dict(os.environ, PATH=str(folder)+os.pathsep+os.environ['PATH'],
                                 FIXTURE_AUTHORITY_STATE=str(state)):
                result = self.run_tasks(tasks, check=check, **values)
            return result, json.loads(state.read_text())

    def test_negative_then_positive_all_authorities_precede_first_recursive_leaf_query(self):
        result, state = self.run_readiness()
        self.assert_ok(result)
        direct = [x for x in state['calls'] if x['server'] in IPS]
        public = [x for x in state['calls'] if x['server'] == '8.8.8.8' and x['name'] == LEAF]
        self.assertEqual(len(direct), 4)  # Remaining queued include rounds must do no work.
        self.assertEqual(len(public), 1)
        self.assertFalse(state['premature_recursive'])
        self.assertTrue(all(x['norecurse'] for x in direct))
        self.assertEqual(state['calls'][-1], public[0])
        self.assertFalse(any(x['name'] == 'v24-test2.example.invalid' for x in state['calls']))

    def test_exhausted_rounds_and_zone_NS_mismatch_never_query_recursive_leaf(self):
        result, state = self.run_readiness({ip: 99 for ip in IPS}, aap_dns_authority_max_rounds=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len([x for x in state['calls'] if x['server'] in IPS]), 4)
        self.assertFalse(any(x['name'] == LEAF and x['server'] == '8.8.8.8' for x in state['calls']))
        result, state = self.run_readiness(mismatch=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(state['calls']), 1)  # Existing zone apex only, never selected name.

    def test_invalid_budget_and_check_mode_do_not_query_selected_name(self):
        result, state = self.run_readiness(aap_dns_authority_max_rounds=0)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state['calls'], [])
        result, state = self.run_readiness(aap_instance_dns_readback={'status': 200, 'json': v3.page([])})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(state['calls'], [])
        result, state = self.run_readiness(check=True)
        self.assert_ok(result)
        self.assertEqual(state['calls'], [])


if __name__ == '__main__':
    unittest.main()
