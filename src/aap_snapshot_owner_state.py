"""Read only selected project state with existing fixed-owner bootstrap readers."""
import base64
from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = spec_from_file_location(name, path); result = module_from_spec(spec); spec.loader.exec_module(result)
    return result


codec = load('aap_snapshot_owner_yaml', ROOT / 'src/cac_yaml.py')
snapshots = load('aap_snapshot_owner_digest', ROOT / 'module_utils/aap_snapshot.py')
OWNERS = {
    'windows_disconnected': ('disconnected-windows-patching', 'vaults/cac/disconnected-windows-patching-cac-vault.yml'),
    'aiops': ('aiops-selfhealing-demo', 'vaults/cac/aiops-selfhealing-demo-cac-vault.yml'),
}


def fingerprint(value):
    return snapshots.digest({'value': value, 'literal_paths': sorted(codec.literal_paths(value), key=repr)})


def selected_state(owner, capture, selected):
    snapshots.require(owner in OWNERS and isinstance(capture, dict)
                      and capture.get('cac_import_metadata', {}).get('project_id') == OWNERS[owner][0],
                      'Read the declared authoritative project capture, not an arbitrary repository document.')
    if owner == 'windows_disconnected':
        profile = capture['windows_disconnected_instance_profiles'].get(selected)
        runtime = capture['windows_disconnected_runtime_ciphertexts'].get(selected)
        snapshots.require((profile is None) == (runtime is None), 'Selected Windows profile/runtime presence differs.')
        if runtime is not None:
            snapshots.require(isinstance(profile, dict) and profile.get('instance') == selected
                              and isinstance(runtime, str) and runtime.startswith('$ANSIBLE_VAULT;'),
                              'Require the selected opaque encrypted Windows runtime.')
        return {'profile': fingerprint(profile), 'opaque_runtime': snapshots.digest(runtime)}
    profile = capture['aiops_instances'].get(selected)
    ciphertext = capture['aiops_runtime_settings_vault']
    key = capture['aiops_playbook_vault_password']
    snapshots.require(isinstance(ciphertext, str) and ciphertext.startswith('$ANSIBLE_VAULT;')
                      and isinstance(key, str) and bool(key), 'Use the existing encrypted AIOps runtime and its native key.')
    runtime = codec.load_repository_yaml(VaultLib([('default', VaultSecret(key.encode()))]).decrypt(ciphertext.encode()))
    snapshots.require(runtime.get('schema_version') == 1 and isinstance(runtime.get('instances'), dict),
                      'Require the existing instance-indexed AIOps runtime schema.')
    selected_runtime = runtime['instances'].get(selected)
    snapshots.require((profile is None) == (selected_runtime is None), 'Selected AIOps profile/runtime presence differs.')
    return {'profile': fingerprint(profile), 'runtime': fingerprint(selected_runtime)}


def read(bootstrap, workspace, selected, central_repository, run=subprocess.run):
    snapshots.require(re.fullmatch(r'aap[0-9]+-test-[1-9][0-9]*', selected or ''), 'Select one actual AAP allocation.')
    workspace = Path(workspace)
    snapshots.require(workspace.is_dir() and not workspace.is_symlink() and workspace.stat().st_uid == os.geteuid()
                      and workspace.stat().st_mode & 0o077 == 0, 'Use only this job private checkout workspace.')
    namespace = central_repository.rsplit('/', 1)[0] + '/'
    states = {}
    for owner, (_, relative) in OWNERS.items():
        credential = bootstrap['cac_bootstrap_git_credentials'][owner]
        vault = bootstrap['cac_bootstrap_vault_credentials'][owner]
        repository = credential['repository_url']; parsed = urlsplit(repository)
        snapshots.require(isinstance(repository, str) and repository.startswith(namespace)
                          and parsed.scheme == 'https' and not parsed.username and not parsed.password
                          and not parsed.query and not parsed.fragment and repository.endswith('.git')
                          and re.fullmatch(r'[A-Za-z0-9_.-]+\.git', repository[len(namespace):]),
                          'Use the fixed-owner HTTPS repository already declared in protected bootstrap.')
        token = credential['token']; password = vault['vault_password']
        snapshots.require(isinstance(token, str) and token and not re.search(r'[\r\n]', token)
                          and isinstance(password, str) and bool(password), 'Retain existing complete owner read/Vault credentials.')
        checkout = workspace / owner; checkout.mkdir(mode=0o700)
        environment = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false', LC_ALL='C',
            GIT_CONFIG_COUNT='4', GIT_CONFIG_KEY_0='credential.helper', GIT_CONFIG_VALUE_0='',
            GIT_CONFIG_KEY_1='http.followRedirects', GIT_CONFIG_VALUE_1='false',
            GIT_CONFIG_KEY_2='http.sslVerify', GIT_CONFIG_VALUE_2='true',
            GIT_CONFIG_KEY_3='http.' + repository + '.extraheader',
            GIT_CONFIG_VALUE_3='Authorization: Basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode())
        def git(*args):
            result = run(['git', '-C', str(checkout), *args], env=environment, capture_output=True, text=True, timeout=60)
            if result.returncode:
                detail = (getattr(result, 'stderr', '') or '')[-4096:]
                for secret in (token, environment['GIT_CONFIG_VALUE_3'].removeprefix('Authorization: Basic ')):
                    detail = detail.replace(secret, '[redacted]')
                raise ValueError('Snapshot state read for %s failed (rc=%d): %s; no VM power operation is permitted.' %
                                 (owner, result.returncode, detail))
            return result.stdout
        git('init', '--quiet'); git('remote', 'add', 'origin', repository)
        git('fetch', '--quiet', '--depth=1', 'origin', 'main')
        ciphertext = git('show', 'FETCH_HEAD:' + relative)
        snapshots.require(ciphertext.startswith('$ANSIBLE_VAULT;'), 'The selected project capture must remain encrypted.')
        capture = codec.load_repository_yaml(VaultLib([('default', VaultSecret(password.encode()))]).decrypt(ciphertext.encode()))
        if owner == 'aiops':
            snapshots.require(git('show', 'FETCH_HEAD:vaults/runtime/aiops-selfhealing-demo-runtime-vault.yml') ==
                              str(capture['aiops_runtime_settings_vault']), 'Standalone and embedded AIOps runtime ciphertext differ.')
        elif selected in capture['windows_disconnected_runtime_ciphertexts']:
            runtime_path = 'vaults/runtime/windows-instance-profile-v%02d.yml' % int(selected.rsplit('-', 1)[1])
            snapshots.require(git('show', 'FETCH_HEAD:' + runtime_path) ==
                              str(capture['windows_disconnected_runtime_ciphertexts'][selected]),
                              'Standalone and embedded selected Windows runtime ciphertext differ.')
        states[owner] = selected_state(owner, capture, selected)
    return states
