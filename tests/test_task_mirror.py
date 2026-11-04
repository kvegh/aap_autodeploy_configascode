"""Keep project task exports complete, private, reproducible and safe on failure."""

from contextlib import redirect_stderr
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('task_mirror', ROOT / 'scripts/sync_todo.py')
MIRROR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIRROR)
CANARY = 'PRIVATE-FULL-TASK-CONTENT-CANARY'
PASSWORD = b'fixture-only-vault-password'


def issue(identifier, labels=None):
    return {'id': identifier, 'title': 'Generic project task', 'status': 'open', 'priority': 2,
        'issue_type': 'task', 'labels': labels or [], 'description': CANARY + ' description',
        'design': CANARY + ' design', 'acceptance_criteria': CANARY + ' acceptance',
        'notes': CANARY + ' notes', 'close_reason': CANARY + ' outcome',
        'created_by': CANARY + ' person', 'owner': CANARY + ' account',
        'revision': '12345', 'comment_count': 0, 'dependencies': [], 'comments': []}


def source_records():
    records = [issue(identifier) for identifier in sorted(MIRROR.RELATED_IDS)]
    records.extend([issue(MIRROR.FAMILY), issue(MIRROR.FAMILY + '.999'), issue(MIRROR.FAMILY + '.999.1'),
        issue('bead-wd-aapfixture', ['aap-autodeploy']), issue('bead-wd-hypervisorfixture', ['hactarconfig']),
        issue('bead-wd-unrelatedfixture', ['unrelated-project'])])
    records[0].update(comment_count=1, comments=[{'id': 11, 'text': CANARY + ' comment',
        'author': CANARY + ' author', 'created_at': '2026-01-01T00:00:00Z'}])
    return records


def fake_beads(records):
    """Simulate the native list/show/comments views without connecting to a DB."""
    by_id = {row['id']: deepcopy(row) for row in records}

    def read(*arguments):
        if arguments[0] == 'list':
            selected = list(by_id.values())
            if '--label-any' in arguments:
                selected = [row for row in selected if MIRROR.PROJECT_LABELS.intersection(row['labels'])]
            return [{key: deepcopy(row[key]) for key in ('id', 'title', 'status', 'priority', 'issue_type', 'labels')}
                    for row in selected]
        if arguments[0] == 'show':
            return [deepcopy(by_id[identifier]) for identifier in arguments[1:] if not identifier.startswith('--')]
        if arguments[0] == 'comments':
            return deepcopy(by_id[arguments[1]]['comments'])
        raise AssertionError('Unexpected tracker command')
    return read


class TaskMirrorTests(unittest.TestCase):
    def test_scope_includes_both_projects_unlabelled_family_and_related_tasks_only(self):
        records = source_records()
        with mock.patch.object(MIRROR, 'read_beads', side_effect=fake_beads(records)) as read:
            selected = MIRROR.load_records()
        expected = {row['id'] for row in records} - {'bead-wd-unrelatedfixture'}
        self.assertEqual({row['id'] for row in selected}, expected)
        self.assertEqual(next(row for row in selected if row['comment_count'])['comments'][0]['text'], CANARY + ' comment')
        self.assertNotIn('bead-wd-hypervisorfixture', {row['id'] for row in MIRROR.public_records(selected)})
        self.assertIn('bead-wd-aapfixture', {row['id'] for row in MIRROR.public_records(selected)})
        self.assertIn('--long', read.call_args_list[2].args)
        self.assertIn('--brief-deps', read.call_args_list[2].args)

    def test_tracker_process_is_readonly_and_failure_does_not_echo_protected_output(self):
        with mock.patch.object(MIRROR.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '[]', '')) as command:
            self.assertEqual(MIRROR.read_beads('list', '--brief'), [])
        self.assertEqual(command.call_args.args[0], ['bd', '--readonly', 'list', '--brief', '--json'])
        with mock.patch.object(MIRROR.subprocess, 'run', side_effect=subprocess.CalledProcessError(2, ['bd'], stderr=CANARY)):
            with self.assertRaises(MIRROR.MirrorError) as failure:
                MIRROR.read_beads('show', MIRROR.FAMILY)
        self.assertNotIn(CANARY, str(failure.exception))

    def test_incomplete_details_comments_and_empty_selection_are_refused(self):
        for change in ('empty', 'missing-detail', 'duplicate-detail', 'missing-metadata', 'missing-comments', 'unscoped'):
            original = fake_beads(source_records())

            def broken(*arguments):
                result = original(*arguments)
                if arguments[0] == 'list' and '--label-any' in arguments:
                    if change == 'empty': return []
                    if change == 'unscoped': result[0]['labels'] = ['unrelated-project']
                elif arguments[0] == 'show':
                    if change == 'missing-detail': result.pop()
                    elif change == 'duplicate-detail': result.append(deepcopy(result[0]))
                    elif change == 'missing-metadata': result[0].pop('comment_count')
                elif arguments[0] == 'comments' and change == 'missing-comments': return []
                return result

            with self.subTest(change=change), mock.patch.object(MIRROR, 'read_beads', side_effect=broken):
                with self.assertRaises(MIRROR.MirrorError):
                    MIRROR.load_records()

    def test_public_overview_excludes_private_bodies_people_and_environment_identifiers(self):
        row = issue('bead-wd-aapfixture', ['aap-autodeploy'])
        private = ['https://demo.v42.example.invalid/path', 'user@private-host', '192.0.2.10',
            'aa:bb:cc:dd:ee:ff', '2001:db8::10', '/opt/private/script.sh', 'config/private.yml',
            '123e4567-e89b-12d3-a456-426614174000', 'testserver-v42', 'aap27-test-42', 'server-ng']
        row['title'] = 'Deploy ' + ' '.join(private) + ' | <script> unsafe'
        row.update(parent=MIRROR.FAMILY, dependencies=[{'id': 'bead-wd-dependency',
            'title': CANARY, 'description': CANARY, 'dependency_type': 'blocks'}])
        output = MIRROR.render([row])
        self.assertNotIn(CANARY, output)
        for value in private:
            with self.subTest(value=value): self.assertNotIn(value, output)
        self.assertNotIn('<script>', output)
        self.assertIn('&#124;', output)
        self.assertIn('bead-wd-dependency', output)
        self.assertIn('| open | P2 | task |', output)

    def prepare_files(self, folder):
        todo = folder / 'TODO.md'
        todo.write_text('existing overview\n')
        snapshot = folder / 'project-task-records.vault.yml'
        password = folder / 'password'
        password.write_bytes(PASSWORD + b'\n')
        password.chmod(0o600)
        return todo, snapshot, password

    def test_native_vault_roundtrip_is_lossless_and_unchanged_rerun_keeps_ciphertext(self):
        records = [issue('bead-wd-aapfixture', ['aap-autodeploy'])]
        records[0].update(dependencies=[{'id': MIRROR.FAMILY, 'dependency_type': 'blocks'}],
            comments=[{'text': CANARY + ' comment', 'author': CANARY + ' person'}], comment_count=1)
        with tempfile.TemporaryDirectory(prefix='task-mirror-vault-') as directory:
            todo, target, password = self.prepare_files(Path(directory))
            self.assertFalse(MIRROR.synchronize(records, todo, target, password, check=True))
            self.assertFalse(target.exists())
            self.assertEqual(todo.read_text(), 'existing overview\n')
            self.assertTrue(MIRROR.synchronize(records, todo, target, password))
            ciphertext, stamp = target.read_bytes(), target.stat().st_mtime_ns
            self.assertTrue(ciphertext.startswith(b'$ANSIBLE_VAULT;1.2;AES256;cac\n'))
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertNotIn(CANARY.encode(), ciphertext)
            self.assertNotIn(CANARY, todo.read_text())
            vault = VaultLib([('cac', VaultSecret(PASSWORD))])
            self.assertEqual(json.loads(vault.decrypt(ciphertext)), MIRROR.snapshot(records))
            self.assertTrue(MIRROR.synchronize(records, todo, target, password, check=True))
            self.assertTrue(MIRROR.synchronize(records, todo, target, password))
            self.assertEqual(target.read_bytes(), ciphertext)
            self.assertEqual(target.stat().st_mtime_ns, stamp)

    def test_stale_private_notes_and_public_status_are_detected_without_check_writes(self):
        records = [issue('bead-wd-aapfixture', ['aap-autodeploy'])]
        with tempfile.TemporaryDirectory(prefix='task-mirror-stale-') as directory:
            todo, target, password = self.prepare_files(Path(directory))
            MIRROR.synchronize(records, todo, target, password)
            original_todo, original_cipher = todo.read_bytes(), target.read_bytes()
            records[0]['notes'] += ' latest decision'
            self.assertFalse(MIRROR.synchronize(records, todo, target, password, check=True))
            self.assertEqual(todo.read_bytes(), original_todo)
            self.assertEqual(target.read_bytes(), original_cipher)
            MIRROR.synchronize(records, todo, target, password)
            self.assertEqual(todo.read_bytes(), original_todo)
            self.assertNotEqual(target.read_bytes(), original_cipher)
            records[0]['status'] = 'closed'
            self.assertFalse(MIRROR.synchronize(records, todo, target, password, check=True))
            MIRROR.synchronize(records, todo, target, password)
            self.assertIn('| closed |', todo.read_text())

    def test_semantically_equal_native_ciphertext_does_not_require_reencryption(self):
        records = [issue('bead-wd-aapfixture', ['aap-autodeploy'])]
        with tempfile.TemporaryDirectory(prefix='task-mirror-semantic-') as directory:
            todo, target, password = self.prepare_files(Path(directory))
            MIRROR.synchronize(records, todo, target, password)
            vault = VaultLib([('cac', VaultSecret(PASSWORD))])
            alternative = vault.encrypt(json.dumps(MIRROR.snapshot(records)), vault_id='cac')
            target.write_bytes(alternative)
            self.assertTrue(MIRROR.synchronize(records, todo, target, password, check=True))
            MIRROR.synchronize(records, todo, target, password)
            self.assertEqual(target.read_bytes(), alternative)

    def test_wrong_password_unrelated_file_and_failed_staging_preserve_existing_outputs(self):
        records = [issue('bead-wd-aapfixture', ['aap-autodeploy'])]
        with tempfile.TemporaryDirectory(prefix='task-mirror-failure-') as directory:
            folder = Path(directory)
            todo, target, password = self.prepare_files(folder)
            MIRROR.synchronize(records, todo, target, password)
            original_todo, original_cipher = todo.read_bytes(), target.read_bytes()
            password.write_bytes(b'wrong-fixture-password')
            with self.assertRaises(MIRROR.MirrorError): MIRROR.synchronize(records, todo, target, password)
            self.assertEqual(todo.read_bytes(), original_todo)
            self.assertEqual(target.read_bytes(), original_cipher)
            password.write_bytes(PASSWORD)
            unrelated = VaultLib([('cac', VaultSecret(PASSWORD))]).encrypt('{"unrelated":true}', vault_id='cac')
            target.write_bytes(unrelated)
            with self.assertRaises(MIRROR.MirrorError): MIRROR.synchronize(records, todo, target, password)
            self.assertEqual(target.read_bytes(), unrelated)
            self.assertEqual(todo.read_bytes(), original_todo)
            target.unlink()
            with self.assertRaises(MIRROR.MirrorError):
                MIRROR.synchronize(records, folder / 'missing' / 'TODO.md', target, password)
            self.assertFalse(target.exists())
            self.assertEqual(list(folder.glob('.project-task-records.vault.yml.*')), [])

    def test_cli_requires_both_existing_secret_and_snapshot_arguments(self):
        for arguments in ([], ['--snapshot-file', 'example.vault.yml'], ['--vault-password-file', 'example-password']):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), mock.patch.object(MIRROR, 'load_records') as load:
                with self.assertRaises(SystemExit) as failure: MIRROR.main(arguments)
                self.assertEqual(failure.exception.code, 2)
                load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
