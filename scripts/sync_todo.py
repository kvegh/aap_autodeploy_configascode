#!/usr/bin/env python3
"""Export selected Beads tasks using a Python interpreter with Ansible installed."""

import argparse
from copy import deepcopy
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT_LABELS = {'aap-autodeploy', 'hactarconfig'}
FAMILY = 'bead-wd-72f'
RELATED_IDS = {'bead-wd-3ix', 'bead-wd-mcr', 'bead-wd-mcr.1', 'bead-wd-zau', 'bead-wd-72v', 'bead-wd-sc8'}
# Ownership moved to separate chats. Keep their full recovery records, while
# omitting the completed handoffs from this project's overview at owner request.
TRANSFERRED_HANDOFFS = {'bead-wd-72f.38', 'bead-wd-72f.39'}
IDENTIFIER = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]*$')
SNAPSHOT_FORMAT = 'beads-project-recovery-export'
VAULT_ID = 'cac'


class MirrorError(Exception):
    """A protected export cannot safely replace its existing files."""


def existing_vault_library(password):
    try:
        from ansible.parsing.vault import VaultLib, VaultSecret
    except ImportError:
        raise MirrorError('Run this tool with the existing Python interpreter that provides Ansible Vault; no dependency was installed.') from None
    return VaultLib([(VAULT_ID, VaultSecret(password))])


def read_beads(*arguments):
    try:
        result = subprocess.run(['bd', '--readonly', *arguments, '--json'], cwd=ROOT,
            capture_output=True, text=True, timeout=120, check=True)
        value = json.loads(result.stdout)
    except Exception:
        raise MirrorError('Read-only Beads export failed; existing files were not changed.') from None
    if not isinstance(value, list):
        raise MirrorError('Beads returned an incomplete response; existing files were not changed.')
    return value


def family_member(identifier):
    return identifier == FAMILY or identifier.startswith(FAMILY + '.')


def valid_identifier(value):
    return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None


def validate_rows(rows):
    if (not rows or any(not isinstance(row, dict) or not valid_identifier(row.get('id')) for row in rows)
            or len({row['id'] for row in rows}) != len(rows)):
        raise MirrorError('Beads returned empty, duplicate or invalid task records; existing files were not changed.')


def load_records():
    # Brief workspace metadata discovers unlabelled descendants without copying
    # unrelated task bodies into this project's recovery export.
    selected = read_beads('list', '--all', '--limit', '0', '--brief', '--label-any', ','.join(sorted(PROJECT_LABELS)))
    validate_rows(selected)
    if any(not isinstance(row.get('labels'), list) or not PROJECT_LABELS.intersection(row['labels']) for row in selected):
        raise MirrorError('Beads returned an unscoped project selection; existing files were not changed.')
    workspace = read_beads('list', '--all', '--limit', '0', '--brief')
    validate_rows(workspace)
    identifiers = {row['id'] for row in selected}
    identifiers.update(row['id'] for row in workspace if family_member(row['id']) or row['id'] in RELATED_IDS)
    if not RELATED_IDS <= identifiers or FAMILY not in identifiers:
        raise MirrorError('Required project tasks are missing; existing files were not changed.')
    # Full own records are retained. Dependency metadata avoids recursively
    # exporting unrelated linked tasks' free text while retaining each edge.
    records = read_beads('show', *sorted(identifiers), '--long', '--brief-deps')
    validate_rows(records)
    if {row['id'] for row in records} != identifiers:
        raise MirrorError('Beads returned incomplete task details; existing files were not changed.')
    for row in records:
        if (not isinstance(row.get('title'), str) or not row['title'].strip()
                or not isinstance(row.get('status'), str) or not re.fullmatch(r'[a-z_]+', row['status'])
                or type(row.get('priority')) is not int or not 0 <= row['priority'] <= 4
                or not isinstance(row.get('issue_type'), str) or not re.fullmatch(r'[a-z-]+', row['issue_type'])
                or type(row.get('comment_count')) is not int or row['comment_count'] < 0
                or not isinstance(row.get('dependencies', []), list)
                or any(not isinstance(edge, dict) or not valid_identifier(edge.get('id'))
                       for edge in row.get('dependencies', []))
                or (row.get('parent') is not None and not valid_identifier(row['parent']))):
            raise MirrorError('Beads returned incomplete task metadata; existing files were not changed.')
        comments = read_beads('comments', row['id']) if row['comment_count'] else []
        if (len(comments) != row['comment_count']
                or any(not isinstance(comment, dict) or not isinstance(comment.get('text'), str) for comment in comments)):
            raise MirrorError('Beads returned incomplete task comments; existing files were not changed.')
        row['comments'] = comments
    return sorted(records, key=lambda row: row['id'])


def public_title(value):
    """Redact common environment identifiers; operators must still review titles."""
    value = ' '.join(value.split())
    patterns = (
        (r'https?://[^\s<>]+', '[URL]'),
        (r'(?<!\w)[A-Za-z_][A-Za-z0-9_.+-]*@[A-Za-z0-9_.-]+', '[ACCOUNT]'),
        (r'\b(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_-]{16,})\b', '[SECRET]'),
        (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]'),
        (r'(?<![\w:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![\w:])', '[MAC]'),
        (r'(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*(?:%[\w.-]+)?(?:/\d{1,3})?(?![\w:])', '[IP]'),
        (r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?![\w.])', '[IP]'),
        (r'\b[A-Za-z]:[\\/][^\s<>"\'|,;)]*', '[PATH]'),
        (r'(?<![\w])(?:~|\.{1,2})?/[^\s<>"\'|,;)]*', '[PATH]'),
        (r'(?<![\w])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_./-]+', '[PATH]'),
        (r'(?<![\w-])(?:[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?\.)+[a-z]{2,63}(?![\w-])', '[HOST]'),
        (r'\b(?:[a-z][a-z0-9-]*[-.]v\d+|aap\d*(?:-test)?-\d+|[a-z][a-z0-9-]*-(?:ng|prod|production|test|dev|stage|staging))\b', '[HOST]'),
    )
    for pattern, replacement in patterns:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    # A title is table text, never a source of Markdown links or HTML.
    return html.escape(value, quote=False).replace('|', '&#124;').replace('`', '&#96;').replace('[', '&#91;').replace(']', '&#93;')


def public_records(records):
    return [row for row in records if not any(row['id'] == task or row['id'].startswith(task + '.')
                                              for task in TRANSFERRED_HANDOFFS)
            and ('aap-autodeploy' in row.get('labels', [])
                 or family_member(row['id']) or row['id'] in RELATED_IDS)]


def render(records):
    rows = public_records(records)
    ordered = sorted(rows, key=lambda row: (row['priority'], row['id']))
    pending = [row for row in ordered if row['status'] != 'closed']
    completed = [row for row in ordered if row['status'] == 'closed']
    lines = ['# AutoDeploy tasks', '',
        'Beads is authoritative. This generated overview includes only sanitized task metadata.',
        'Full selected AutoDeploy and hypervisor task records, decisions and comments are',
        'preserved in the separate Ansible Vault-encrypted recovery export. Refresh both',
        'outputs together with `python3 scripts/sync_todo.py --snapshot-file <protected-export> --vault-password-file <existing-password-file>`;',
        'add `--check` to detect stale output without writing. Review public titles before committing.', '',
        'Scope, notes, acceptance criteria, outcomes, comment bodies and personal metadata',
        'are excluded here. Hypervisor-only tasks remain in that project\'s own overview.',
        'See [object ownership and label coverage](docs/cac-object-ownership.md) and',
        '[recovery and use-case targets](docs/recovery-and-use-case-targets.md) for agreed design context.', '',
        f'{len(rows)} tasks: {len(pending)} outstanding; {len(completed)} closed.', '']
    for heading, group in (('Outstanding tasks', pending), ('Tasks already done/implemented/decided against', completed)):
        lines.extend(['## ' + heading, '', '| Task | Title | Status | Priority | Type | Parent / dependency IDs |',
                      '|---|---|---|---|---|---|'])
        for row in group:
            related = sorted({edge['id'] for edge in row.get('dependencies', [])} | ({row['parent']} if row.get('parent') else set()))
            lines.append('| ' + ' | '.join((row['id'], public_title(row['title']), row['status'],
                'P' + str(row['priority']), row['issue_type'], ', '.join(related) or '—')) + ' |')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def snapshot(records):
    return {'format': SNAPSHOT_FORMAT, 'format_version': 1,
        'scope': {'labels': sorted(PROJECT_LABELS), 'family': FAMILY, 'related_ids': sorted(RELATED_IDS)},
        'records': deepcopy(sorted(records, key=lambda row: row['id']))}


def read_existing_snapshot(path, vault):
    if not path.exists():
        return None
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError('Require an existing regular export file')
        raw = path.read_bytes()
        if not raw.startswith(b'$ANSIBLE_VAULT;1.2;AES256;cac\n'):
            raise ValueError('Require the fixed named Vault format')
        existing = json.loads(vault.decrypt(raw))
        if (not isinstance(existing, dict) or existing.get('format') != SNAPSHOT_FORMAT
                or existing.get('format_version') != 1 or not isinstance(existing.get('records'), list)
                or existing.get('scope') != snapshot([])['scope']):
            raise ValueError('Do not replace an unrelated encrypted file')
        return existing
    except Exception:
        raise MirrorError('Existing task export cannot be decrypted or has another format; existing files were not changed.') from None


def stage_file(path, content, mode):
    if path.is_symlink() or not path.parent.is_dir():
        raise MirrorError('Output must use an existing directory and a regular file; existing files were not changed.')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return Path(temporary)


def synchronize(records, destination, snapshot_file, password_file, check=False):
    if destination.resolve() == snapshot_file.resolve():
        raise MirrorError('Use separate overview/export files; existing files were not changed.')
    try:
        password = password_file.read_bytes().strip()
        if not password:
            raise ValueError('Empty Vault password file')
    except Exception:
        raise MirrorError('The existing Vault password file could not be read; existing files were not changed.') from None
    vault = existing_vault_library(password)
    desired_snapshot = snapshot(records)
    current_snapshot = read_existing_snapshot(snapshot_file, vault)
    content = render(records).encode('utf-8')
    if destination.is_symlink() or snapshot_file == destination:
        raise MirrorError('Use separate regular overview/export files; existing files were not changed.')
    overview_matches = destination.is_file() and destination.read_bytes() == content
    snapshot_matches = current_snapshot == desired_snapshot
    if check:
        return overview_matches and snapshot_matches
    staged = []
    try:
        # Stage both replacements before either rename. Plain task data is
        # encrypted in memory and is never written to a temporary plaintext file.
        if not snapshot_matches:
            plaintext = json.dumps(desired_snapshot, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
            ciphertext = vault.encrypt(plaintext, vault_id=VAULT_ID)
            if json.loads(vault.decrypt(ciphertext)) != desired_snapshot:
                raise MirrorError('Encrypted task export roundtrip failed; existing files were not changed.')
            staged.append((stage_file(snapshot_file, ciphertext, 0o600), snapshot_file))
        if not overview_matches:
            staged.append((stage_file(destination, content, 0o644), destination))
        for temporary, target in staged:
            os.replace(temporary, target)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-file', required=True, type=Path,
        help='Existing recovery repository destination for the full encrypted export.')
    parser.add_argument('--vault-password-file', required=True, type=Path,
        help='Existing CaC Vault password file; no key is created or printed.')
    parser.add_argument('--check', action='store_true', help='Check both outputs against Beads without writing.')
    arguments = parser.parse_args(argv)
    try:
        records = load_records()
        fresh = synchronize(records, ROOT / 'TODO.md', arguments.snapshot_file, arguments.vault_password_file, arguments.check)
        if not fresh:
            print('Task overview or protected export is stale; refresh both outputs together.', file=sys.stderr)
            return 1
        print('Task overview and protected export match Beads.' if arguments.check else 'Updated task overview and protected export from Beads.')
        return 0
    except MirrorError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception:
        print('Task export failed; inspect protected inputs and retry. No plaintext task backup was written.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
