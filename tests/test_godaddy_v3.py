"""Exercise the real DNS task includes and URI module against a local HTTP fixture."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

os.environ.setdefault('ANSIBLE_LOCAL_TEMP', '/tmp/aap-v3-dns-unit-local')
from ansible.errors import AnsibleFilterError
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('godaddy_v3_test', ROOT / 'filter_plugins/godaddy_v3.py')
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)


def record(identifier='fixture/id', name='appliance.v24-test', address='192.0.2.10', ttl=600, kind='A'):
    return {'recordId': identifier, 'name': name, 'data': address, 'ttl': ttl, 'type': kind}


def page(records, total=None, pages=1, links=None):
    return {'items': records, 'totalItems': len(records) if total is None else total,
            'totalPages': pages, 'links': links or []}


class PageValidationTests(unittest.TestCase):
    def test_complete_pages_reject_truncation_malformed_totals_and_duplicate_ids(self):
        self.assertEqual(filters.godaddy_v3_records(page([])), [])
        self.assertEqual(filters.godaddy_v3_records({'items': [], 'links': []}), [])
        for invalid in [[], {}, {'items': [], 'totalItems': 0},
                        {'items': [], 'links': [{'rel': 'next'}]},
                        {'items': [record()]}, page([record()], total=2),
                        page([record()], pages=2), page([record()], links=[{'rel': 'next'}]),
                        page([record(), record()]), page([record('..')]),
                        page([record(ttl=True)]), page([record(ttl=0)]),
                        page([], total=True), page([], pages=-1)]:
            with self.subTest(invalid=invalid), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_records(invalid)
        for invalid in [page([record(name='other')]), page([record(kind='AAAA')])]:
            with self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_records(invalid, 'appliance.v24-test', 'A')

    def test_accumulation_requires_sequential_stable_exact_totals_and_unique_ids(self):
        first = page([record()], total=2, pages=2, links=[{'rel': 'next'}])
        state = filters.godaddy_v3_accumulate(first, 1)
        self.assertFalse(state['complete'])
        final = filters.godaddy_v3_accumulate(page([record('second')], total=2, pages=2), 2, state)
        self.assertTrue(final['complete'])
        self.assertEqual(len(final['records']), 2)
        for value, number in [(page([record('second')], total=3, pages=2), 2),
                              (page([record()], total=2, pages=2), 2),
                              (page([], total=2, pages=2), 2),
                              (page([record('second')], total=2, pages=2), 3),
                              (page([record('second')], total=2, pages=2,
                                    links=[{'rel': 'next'}]), 2)]:
            with self.subTest(value=value, number=number), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_accumulate(value, number, state)
        self.assertTrue(filters.godaddy_v3_accumulate(page([], pages=0), 1)['complete'])
        self.assertTrue(filters.godaddy_v3_accumulate({'items': [], 'links': []}, 1)['complete'])


class NativeTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
        if not cls.executable:
            raise unittest.SkipTest('Native ansible-playbook is unavailable; no dependencies installed')
        cls.state = {}
        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, status, data=None):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                if status == 302:
                    self.send_header('Location', '/must-not-follow')
                self.end_headers()
                if data is not None:
                    self.wfile.write(json.dumps(data).encode())

            def do_GET(self):
                parsed = urlsplit(self.path)
                q = parse_qs(parsed.query)
                cls.state['calls'].append(('GET', self.path, None))
                if cls.state.get('get_error'):
                    return self.send(cls.state['get_error'], {'error': 'fixture refusal'})
                values = copy.deepcopy(cls.state['records'])
                if 'name' in q:
                    values = [r for r in values if r['name'] == q['name'][0] and r['type'] == q['type'][0]]
                    body = page(values)
                    if not values:
                        body = {'items': [], 'links': []}
                    if cls.state.get('filtered_truncated'):
                        body['totalItems'] = len(values) + 1
                        body['totalPages'] = 2
                else:
                    number = int(q['page'][0])
                    size = cls.state.get('page_size', 100)
                    body = page(values[(number-1)*size:number*size], total=len(values),
                                pages=max(1, (len(values)+size-1)//size))
                    if number > 1 and cls.state.get('duplicate_page'):
                        body['items'] = values[:size]
                    if cls.state.get('truncated_total'):
                        body['totalItems'] += 1
                    if not values:
                        body = {'items': [], 'links': []}
                self.send(200, body)

            def body(self):
                return json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))

            def do_POST(self):
                body = self.body()
                cls.state['calls'].append(('POST', self.path, body))
                new = dict(body, recordId='created/id')
                cls.state['records'].append(new)
                self.send(cls.state.get('post_status', 201), new)

            def do_PUT(self):
                body = self.body()
                cls.state['calls'].append(('PUT', self.path, body))
                identifier = unquote(urlsplit(self.path).path.split('/dns-records/', 1)[1])
                for i, old in enumerate(cls.state['records']):
                    if old['recordId'] == identifier:
                        cls.state['records'][i] = dict(body, recordId=identifier)
                        return self.send(200, cls.state['records'][i])
                self.send(404)

            def do_DELETE(self):
                cls.state['calls'].append(('DELETE', self.path, None))
                identifier = unquote(urlsplit(self.path).path.split('/dns-records/', 1)[1])
                matches = [r for r in cls.state['records'] if r['recordId'] == identifier]
                cls.state['records'][:] = [r for r in cls.state['records'] if r['recordId'] != identifier]
                self.send(404 if cls.state.get('delete_race') or not matches else 204)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), API)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.state.clear()
        self.state.update(records=[], calls=[])

    def run_tasks(self, tasks, check=False, **overrides):
        values = {'vault_domain': 'example.invalid', 'vault_godaddy_api_token': 'fixture-not-a-secret',
                  'aap_test_subdomain': 'appliance.v24-test',
                  'aap_instance_route': {'hypervisor': {'public_ip': '192.0.2.10'}}}
        values.update(overrides)
        with tempfile.TemporaryDirectory(prefix='aap-v3-dns-native-') as folder:
            folder = Path(folder)
            fixture_tasks = folder / 'tasks'
            fixture_tasks.mkdir()
            for source in (ROOT / 'tasks').glob('*dns*.yml'):
                # Fixture-only transport substitution; production has a fixed HTTPS origin.
                copied = source.read_text().replace('https://api.godaddy.com',
                                                    'http://127.0.0.1:' + str(self.server.server_port))
                (fixture_tasks / source.name).write_text(copied)
            tasks = copy.deepcopy(tasks)
            for task in tasks:
                include = task.get('ansible.builtin.include_tasks')
                if isinstance(include, str) and include.startswith(str(ROOT / 'tasks') + '/'):
                    task['ansible.builtin.include_tasks'] = str(fixture_tasks / Path(include).name)
            play = folder / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                            'gather_facts': False, 'vars': values, 'tasks': tasks}], sort_keys=False))
            cfg = folder / 'ansible.cfg'
            cfg.write_text('[defaults]\nfilter_plugins=' + str(ROOT / 'filter_plugins') + '\n')
            command = [self.executable, '-i', 'localhost,', str(play)]
            if check:
                command.append('--check')
            return subprocess.run(command,
                                  capture_output=True, text=True, timeout=90,
                                  env=dict(os.environ, ANSIBLE_CONFIG=str(cfg), ANSIBLE_NOCOLOR='1',
                                           ANSIBLE_LOCAL_TEMP=str(folder / 'local'),
                                           ANSIBLE_REMOTE_TEMP=str(folder / 'remote')))

    def reconcile(self):
        return self.run_tasks([{'ansible.builtin.include_tasks': str(ROOT / 'tasks/aap-instance-dns.yml')}])

    def retire(self, reviewed):
        return self.run_tasks([{'ansible.builtin.include_tasks': str(ROOT / 'tasks/decommission-dns-delete.yml')}],
                              aap_dns_retire_record={'name': 'appliance.v24-test', 'type': 'A', 'records': reviewed})

    def writes(self):
        return [x for x in self.state['calls'] if x[0] != 'GET']

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_repeat_update_and_retire_preserve_unrelated_records(self):
        unrelated = record('unrelated', 'other', '192.0.2.20')
        self.state['records'] = [unrelated]
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        owned = next(r for r in self.state['records'] if r['name'] == 'appliance.v24-test')
        owned['ttl'] = 3600
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST', 'PUT'])
        self.assertIn('created%2Fid', self.writes()[-1][1])
        owned = next(r for r in self.state['records'] if r['name'] == 'appliance.v24-test')
        self.assert_ok(self.retire([copy.deepcopy(owned)]))
        self.assertEqual(self.state['records'], [unrelated])
        self.assert_ok(self.retire([owned]))
        self.assertEqual([x[0] for x in self.writes()], ['POST', 'PUT', 'DELETE'])

    def test_conflicts_multiple_As_and_truncated_pages_refuse_without_writes(self):
        for records in [[record(address='192.0.2.20')],
                        [record(kind='AAAA', address='2001:db8::1')],
                        [record(kind='CNAME', address='other.example.invalid')],
                        [record(), record('second')]]:
            with self.subTest(records=records):
                self.state.update(records=records, calls=[])
                self.assertNotEqual(self.reconcile().returncode, 0)
                self.assertEqual(self.writes(), [])
        self.state.update(records=[], calls=[], filtered_truncated=True)
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual(self.writes(), [])

    def test_provider_error_and_uncertain_POST_are_never_replayed(self):
        self.state['get_error'] = 401
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual(self.writes(), [])
        self.state.pop('get_error')
        self.state.update(calls=[], post_status=500)
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        self.assertEqual(len(self.state['records']), 1)

    def test_provider_redirect_is_not_followed(self):
        self.state['get_error'] = 302
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual(len(self.state['calls']), 3)  # One GET per explicit conflict type.
        self.assertFalse(any('/must-not-follow' in x[1] for x in self.state['calls']))
        self.assertEqual(self.writes(), [])

    def test_retirement_refuses_changed_owner_ID_and_accepts_already_deleted_race(self):
        old = record()
        self.state['records'] = [dict(old, recordId='replacement')]
        self.assertNotEqual(self.retire([old]).returncode, 0)
        self.assertEqual(self.writes(), [])
        self.state.update(records=[old], calls=[], delete_race=True)
        self.assert_ok(self.retire([old]))
        self.assertEqual([x[0] for x in self.writes()], ['DELETE'])
        self.assertEqual(self.state['records'], [])

    def test_zone_pagination_reads_all_pages_and_rejects_duplicates_or_truncation(self):
        tasks = [{'ansible.builtin.set_fact': {'aap_dns_zone_state': {}, 'aap_dns_zone_complete': False}},
                 {'ansible.builtin.include_tasks': str(ROOT / 'tasks/decommission-dns-page.yml'),
                  'loop': '{{ range(1, 5) | list }}', 'loop_control': {'loop_var': 'aap_dns_page_number'},
                  'when': 'not aap_dns_zone_complete'},
                 {'ansible.builtin.assert': {'that': ['aap_dns_zone_complete', 'aap_dns_zone_records | length == 2']}}]
        self.state.update(records=[record(), record('second', 'other')], page_size=1)
        self.assert_ok(self.run_tasks(tasks))
        self.assertEqual(len(self.state['calls']), 2)
        self.state.update(calls=[], duplicate_page=True)
        self.assertNotEqual(self.run_tasks(tasks).returncode, 0)
        self.assertEqual(self.writes(), [])
        self.state.pop('duplicate_page')
        self.state.update(calls=[], truncated_total=True)
        self.assertNotEqual(self.run_tasks(tasks).returncode, 0)
        self.assertEqual(self.writes(), [])

    def test_empty_zone_without_totals_completes_after_only_one_native_read(self):
        tasks = [{'ansible.builtin.set_fact': {'aap_dns_zone_state': {}, 'aap_dns_zone_complete': False}},
                 {'ansible.builtin.include_tasks': str(ROOT / 'tasks/decommission-dns-page.yml'),
                  'loop': '{{ range(1, 5) | list }}', 'loop_control': {'loop_var': 'aap_dns_page_number'},
                  'when': 'not aap_dns_zone_complete'},
                 {'ansible.builtin.assert': {'that': ['aap_dns_zone_complete', 'aap_dns_zone_records == []']}}]
        self.assert_ok(self.run_tasks(tasks))
        self.assertEqual(len(self.state['calls']), 1)
        self.assertEqual(self.writes(), [])


if __name__ == '__main__':
    unittest.main()
