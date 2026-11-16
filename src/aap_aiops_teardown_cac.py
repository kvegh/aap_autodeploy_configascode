"""Append one Source workload teardown JT to a fresh existing encrypted capture.

No controller calls, Git operations or owner/reservation changes. The caller
must integrate against the latest native publisher HEAD, never replace a newer
capture with an older encrypted candidate.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path

from ansible.parsing.vault import VaultLib, VaultSecret
import yaml
import cac_yaml as codec

NAME = 'Teardown AIOps Workload'
BASE = 'Decommission AAP Test Instance'


def candidate(capture):
    result = deepcopy(capture)
    rows = result['autodeploy_configuration']['job_templates']
    bases = [row for row in rows if row.get('name') == BASE]
    if len(bases) != 1:
        raise ValueError('Require the existing exact guarded Source retirement template.')
    base = bases[0]
    if (base.get('playbook') != 'destroy-test-aap.yml' or len(base.get('credentials', [])) != 6
            or base.get('allow_simultaneous') is not False or base.get('job_type') != 'run'
            or any(base.get(field) is not False for field in ('ask_inventory_on_launch', 'ask_limit_on_launch',
                       'ask_credential_on_launch', 'ask_execution_environment_on_launch'))):
        raise ValueError('The existing native Source access and launch guards changed; review before appending.')
    template = deepcopy(base)
    template.update(name=NAME, playbook='teardown-aiops-workload.yml', timeout=10800,
                    description='Preview or retire one exact AIOps workload while preserving its AAP VM, allocation and shared infrastructure.',
                    allow_simultaneous=False, ask_variables_on_launch=False, ask_scm_branch_on_launch=False,
                    survey_enabled=True, survey_spec={'name': 'Select exact AIOps workload cleanup',
                    'description': 'Preserve the selected AAP VM, hypervisor and every shared or unrelated owner.', 'spec': [
                        {'question_name': 'Registered AAP VM owner', 'question_description': 'Exact active reservation VM name, without an inventory alias.',
                         'required': True, 'type': 'text', 'variable': 'aap_instance_key', 'min': 1, 'max': 63, 'default': ''},
                        {'question_name': 'Mode', 'question_description': 'Preview is read-only; apply removes only proved owned workload resources.',
                         'required': True, 'type': 'multiplechoice', 'variable': 'aap_aiops_teardown_mode',
                         'choices': 'preview\napply', 'default': 'preview'},
                        {'question_name': 'Confirm the same instance name', 'question_description': 'Exact selected workload owner; its AAP VM remains.',
                         'required': True, 'type': 'text', 'variable': 'aap_aiops_teardown_confirmation', 'min': 1, 'max': 63, 'default': ''}]})
    matches = [row for row in rows if row.get('name') == NAME]
    if matches:
        if matches != [template]:
            raise ValueError('An existing teardown definition differs; preserve it for review.')
        return result
    rows.append(template)
    inverse = deepcopy(result)
    inverse['autodeploy_configuration']['job_templates'].pop()
    if inverse != capture or codec.literal_paths(inverse) != codec.literal_paths(capture):
        raise ValueError('The one-template append changed unrelated native state.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--vault-password-file', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.capture.resolve():
        parser.error('Write a separate protected candidate for review; preserve the fresh input.')
    os.umask(0o077)
    vault = VaultLib([('default', VaultSecret(args.vault_password_file.read_bytes().strip()))])
    original = args.capture.read_bytes()
    before = codec.load_repository_yaml(vault.decrypt(original))
    after = candidate(before)
    header = original.splitlines()[0].decode().split(';')
    encoded = vault.encrypt(yaml.dump(after, Dumper=codec.VaultDumper, sort_keys=False, width=110),
                            vault_id=header[3] if len(header) == 4 else None)
    restored = codec.load_repository_yaml(vault.decrypt(encoded))
    if (encoded.splitlines()[0] != original.splitlines()[0] or restored != after
            or codec.literal_paths(restored) != codec.literal_paths(after)):
        raise ValueError('Candidate encryption changed native types, literals or Vault identity.')
    args.output.write_bytes(encoded)
    args.output.chmod(0o600)
    print(json.dumps({'new_template': NAME, 'changed': after != before, 'typed_one_template_inverse': True,
                      'vault_header_and_literals_preserved': True, 'native_mutations': 0}))


if __name__ == '__main__':
    main()
