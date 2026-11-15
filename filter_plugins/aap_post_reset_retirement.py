"""Validate an actual replacement-host job before retiring old metadata only."""

from copy import deepcopy
from datetime import datetime, timezone
import base64
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = spec_from_file_location(name, ROOT / relative)
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


keys = load('post_reset_instance_keys', 'src/aap_instance_keys.py')
decommission = load('post_reset_resources', 'filter_plugins/aap_decommission.py')
WINDOWS_ROLES = {'repo-ext', 'repo-int', 'win2022-managed', 'win2025-managed', 'win-ad'}
ROLES = WINDOWS_ROLES | {'aap', 'zabbix', 'testserver1', 'tra'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def source_operations(client, shared, configuration, hactar, context, settings, proof):
    """Retire old policy on the proved fresh Hactar alias, preserving its trust."""
    keys.require(proof.get('verified') is True and proof.get('expectation') == settings['expectation']
                 and proof.get('source_job', {}).get('template_id') == settings['verification']['template_id']
                 and proof.get('source_job', {}).get('project_revision') == settings['verification']['project_revision'],
                 'Use the actual verified replacement proof for the Hactar alias transition.')
    actual = proof['actual']
    replacement = dict(inventory_id=settings['verification']['inventory_id'], address=actual['target_ipv4'],
                       machine_id=actual['machine_id'], host_keys=actual['host_keys'])
    return keys.source_inventory_operations(client, shared, configuration, hactar, context,
                                             keys.source_retirement_variables, replacement)


def protected_settings(configuration, selected):
    settings = configuration.get('aap_post_reset_retirement')
    keys.require(isinstance(settings, dict) and set(settings) == {'expectation', 'verification'},
                 'Read the protected post-reset retirement expectation and reviewed verifier binding.')
    expected, binding = settings['expectation'], settings['verification']
    keys.require(isinstance(expected, dict) and expected.get('schema_version') == 1
                 and expected.get('instance_name') == selected and isinstance(binding, dict)
                 and set(binding) == {'template_id', 'project_id', 'project_revision', 'inventory_id'}
                 and all(isinstance(binding[field], int) and not isinstance(binding[field], bool)
                         and binding[field] > 0 for field in ('template_id', 'project_id', 'inventory_id'))
                 and isinstance(binding['project_revision'], str)
                 and re.fullmatch(r'[a-f0-9]{40}', binding['project_revision']),
                 'Bind retirement to the selected instance and the reviewed native verification job.')
    return deepcopy(settings)


def combined_context(configuration, shared, hactar, allocation, client, selected, application, expected):
    """Compose existing Windows and AAP retirement helpers, keeping original pins."""
    records = [row for row in allocation['aap_vm_allocation']['reservations'].values()
               if row.get('vm_name') == selected]
    keys.require(len(records) == 1, 'Keep the exact old reservation while verifying reset retirement.')
    record = records[0]
    route = keys._routing.instance_route(record['instance_route'])
    pin = route['hypervisor']
    keys.require(expected.get('previous_pin') == pin and expected.get('aap_hostname') == route['aap_hostname']
                 and isinstance(expected.get('guests'), list) and len(expected['guests']) == 9
                 and {row.get('role') for row in expected['guests']} == ROLES,
                 'The protected reset expectation must retain all nine exact old guest owners.')
    expected_roles = {row['role']: row for row in expected['guests']}
    proof = keys.source_related_resources(client, shared, allocation['aap_vm_allocation'], selected, application)
    keys.require(set(proof['related_resources']) == {'zabbix', 'testserver1', 'tra'},
                 'Retain complete authoritative application ownership until reset absence is proved.')
    working = {'autodeploy': deepcopy(configuration), 'shared': deepcopy(shared), 'hactar': deepcopy(hactar)}
    contexts, guests = [], []
    for role in sorted(WINDOWS_ROLES):
        row = expected_roles[role]
        context = keys.generic_retirement_context(working['autodeploy'], working['shared'], client,
                    row['name'], pin, guest_kind='windows')
        guest = context['guest']
        keys.require(guest is not None and guest.get('instance_name') == selected,
                     'Every selected Windows role needs its current exact trusted ownership record.')
        guests.append(dict(role=role, name=guest['vm_name'], uuid=guest['uuid'], disk=guest['disk']))
        contexts.append(context)
        for kind in working:
            working[kind] = keys.generic_retirement_capture(working[kind], context, kind)
    recovery = [row for row in working['autodeploy']['autodeploy_configuration']['inventories']
                if keys.inventory_variables(row).get('aap_hypervisor_pin') == pin]
    keys.require(len(recovery) == 1, 'Keep the exact old recovery pin before retiring metadata.')
    values = keys.inventory_variables(recovery[0])
    previous = keys._routing.isolation_policy(pin, values.get('aap_hypervisor_isolation_https_clients', []),
        values.get('aap_hypervisor_isolation_protected_ipv4', []), values.get('aap_hypervisor_isolation_host_clients', []),
        values.get('aap_hypervisor_isolation_released_clients', []), values.get('aap_hypervisor_isolation_http_clients', []))
    resources = dict(record['instance_resources'], **proof['related_resources'])
    identities = [{'bridge': nic['bridge'], 'ipv4': nic['address'], 'mac': nic['mac']}
                  for resource in resources.values() for nic in keys._management.primary_interfaces(resource, pin)]
    selected_identities = {tuple(row[field] for field in ('bridge', 'ipv4', 'mac')) for row in identities}
    desired = deepcopy(previous)
    for field in ('https_clients', 'guest_host_clients', 'released_clients', 'http_clients'):
        if field not in desired:
            continue
        retained = [row for row in desired[field]
                    if tuple(row[key] for key in ('bridge', 'ipv4', 'mac')) not in selected_identities]
        if retained != desired[field]:
            if retained:
                desired[field] = retained
            else:
                desired.pop(field)
                if not any(desired.get(key) for key in ('https_clients', 'released_clients', 'http_clients')):
                    desired.pop('protected_ipv4', None)
    context = keys.isolation_retirement_context(record, selected, route['aap_hostname'],
        dict(previous_policy=previous, desired_policy=desired, identities=identities), proof['related_resources'])
    contexts.append(context)
    for role, resource in resources.items():
        guests.append(dict(role=role, name=selected if role == 'aap' else resource['vm_name'],
                           uuid=resource['uuid'], disk=resource['disk']))
    sort_guests = lambda rows: sorted(rows, key=lambda row: row['role'])
    keys.require(sort_guests(guests) == sort_guests(expected['guests']),
                 'Current Windows, AAP and application identities differ from the reset expectation.')
    combined = deepcopy(contexts[0])
    combined.update(route=route, guests=[guest for item in contexts for guest in item['guests']],
        identities=[identity for item in contexts for identity in item['identities']],
        desired_policy=context['desired_policy'],
        removed_rules=set().union(*(item['removed_rules'] for item in contexts)))
    resource_paths = decommission.resources(route, expected['public_zone'], '/opt/vms', resources)
    paths = resource_paths['nginx'] + resource_paths['website_paths'] + [resource_paths['authority']]
    for name in resource_paths['certificates']:
        paths += ['/etc/letsencrypt/live/' + name, '/etc/letsencrypt/archive/' + name,
                  '/etc/letsencrypt/renewal/' + name + '.conf']
    keys.require(expected.get('paths') == sorted(paths),
                 'Reset absence paths must match the exact selected proxy, website and certificate resources.')
    # The application owns its successful ordinary host grants until this point.
    app_clients = application['aiops_instances'][selected]['zabbix']['configuration']['firewall']['guest_host_clients']
    for client_row in app_clients:
        keys.require(all(client_row.get(field) == resources['zabbix'][source]
                         for field, source in (('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))),
                     'Application host permissions must retain their exact selected Zabbix owner.')
        combined['removed_rules'].update('rule family="ipv4" priority="0" source address="%s/32" '
            'destination address="%s/32" port port="%s" protocol="tcp" accept'
            % (client_row['ipv4'], destination, port)
            for destination in client_row['destinations'] for port in client_row['ports'])
    rules = [dict(zone='libvirt', rule=rule) for rule in sorted(combined['removed_rules'])]
    keys.require(expected.get('rich_rules') == rules,
                 'Reset absence must cover all exact ordinary base and application host grants.')
    keys.verify_remaining_guest_grants(combined['desired_policy'], proof)
    application_context = dict(context, removed_rules=combined['removed_rules'])
    for kind in working:
        working[kind] = keys.retire_inventory_capture(working[kind], application_context, kind)
        keys.require(keys.retire_inventory_capture({'autodeploy': configuration, 'shared': shared, 'hactar': hactar}[kind],
                     combined, kind) == working[kind], 'Composed metadata retirement must match the existing exact helpers.')
    return combined, proof, resource_paths


def verified_job(client, job_id, settings, now=None, retirement_job=None, source_inventory_id=None):
    """Fetch actual native completion; callers cannot submit a claimed proof blob."""
    keys.require(isinstance(job_id, int) and not isinstance(job_id, bool) and job_id > 0,
                 'Select the actual successful replacement verification job ID.')
    binding = settings['verification']
    job = client.request('GET', 'jobs/%s/' % job_id)
    keys.require(job.get('id') == job_id and job.get('status') == 'successful'
                 and job.get('failed') is False and job.get('job_template') == binding['template_id']
                 and job.get('project') == binding['project_id'] and job.get('inventory') == binding['inventory_id']
                 and job.get('scm_revision') == binding['project_revision'] and job.get('processed_events') is True,
                 'Require completed native verification from the protected template, project, inventory and revision.')
    proof = job.get('artifacts', {}).get('hactar_recovery_target_details', {}).get('retirement_absence')
    keys.require(isinstance(proof, dict) and set(proof) == {'schema_version', 'verified', 'expectation',
        'expectation_sha256', 'evidence', 'actual', 'source_job', 'checked_at', 'remote_checked_at'}
                 and proof.get('schema_version') == 1 and proof.get('verified') is True
                 and proof.get('expectation') == settings['expectation']
                 and proof.get('expectation_sha256') == digest(settings['expectation'])
                 and proof.get('source_job') == {'id': job_id, 'template_id': binding['template_id'],
                                                'project_revision': binding['project_revision']},
                 'Native reset proof must identify this actual job and the exact protected expectation.')
    def timestamp(value):
        keys.require(isinstance(value, str), 'Require complete native verification timestamps.')
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        keys.require(parsed.utcoffset() is not None, 'Require explicit native verification time zones.')
        return parsed.astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    started, checked, finished = (timestamp(value) for value in (job.get('started'), proof.get('checked_at'), job.get('finished')))
    # The job's controller attests after validating the remote read. Preserve
    # the authenticated host clock separately; clock offset is not freshness.
    timestamp(proof.get('remote_checked_at'))
    keys.require(started <= checked <= finished <= current and (current - checked).total_seconds() <= 1800,
                 'Use a fresh completed verification proof from within its actual job execution.')
    actual = proof.get('actual', {})
    keys.require(isinstance(actual, dict) and set(actual) == {'machine_id', 'host_keys', 'provider_identity',
        'hardware', 'target_ipv4', 'source_ipv4', 'all_ipv4_addresses'}, 'Require complete replacement identity evidence.')
    old = settings['expectation']['previous_pin']
    keys._routing.ipv4(actual['target_ipv4'])
    keys._routing.ipv4(actual['source_ipv4'])
    keys.require(isinstance(actual.get('machine_id'), str) and re.fullmatch(r'[a-f0-9]{32}', actual['machine_id'])
                 and actual['machine_id'] != old['machine_id'] and actual.get('hardware') == settings['expectation']['hardware']
                 and actual.get('target_ipv4') == old['address'] and actual.get('source_ipv4') != old['address']
                 and isinstance(actual.get('all_ipv4_addresses'), list)
                 and old['address'] in actual['all_ipv4_addresses']
                 and actual.get('source_ipv4') not in actual['all_ipv4_addresses'],
                 'Verify a different authenticated installation on the same independently pinned nonproduction hardware.')
    keys._routing.host_keys(actual.get('host_keys'))
    keys._routing.host_keys(old['host_keys'])
    new_keys, old_keys = actual['host_keys'], old['host_keys']
    def fingerprints(values):
        return sorted('SHA256:' + base64.b64encode(hashlib.sha256(
            base64.b64decode(value.split()[1], validate=True)).digest()).decode().rstrip('=') for value in values)
    keys.require(len(new_keys) == 3 and len(set(fingerprints(new_keys))) == 3
                 and {value.split()[0] for value in new_keys} == {'ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'}
                 and not set(fingerprints(new_keys)).intersection(fingerprints(old_keys)),
                 'All replacement host keys must be fresh and differ from every previous trusted key.')
    provider = actual.get('provider_identity')
    keys.require(isinstance(provider, dict) and set(provider) == {'server_number', 'host_fingerprints', 'image'}
                 and provider['server_number'] == settings['expectation']['provider_server_number']
                 and provider['host_fingerprints'] == fingerprints(new_keys)
                 and isinstance(provider['image'], str) and bool(provider['image'].strip()),
                 'Bind every replacement key to the exact independently pinned provider installation.')
    evidence = proof.get('evidence')
    evidence_fields = {'schema_version', 'complete', 'checked_at', 'machine_id', 'host_keys', 'hardware',
        'paths', 'guest_inventory', 'blockdevices', 'mounts', 'nftables', 'firewalld_xml',
        'legacy_ipv4_tables', 'iptables_save'}
    keys.require(isinstance(evidence, dict) and set(evidence) == evidence_fields
                 and evidence['schema_version'] == 1 and evidence['complete'] is True
                 and evidence['checked_at'] == proof['remote_checked_at']
                 and evidence['machine_id'] == actual['machine_id'] and evidence['host_keys'] == new_keys
                 and evidence['hardware'] == actual['hardware']
                 and evidence['guest_inventory'] == {'saved': 0, 'runtime': 0, 'running': 0},
                 'Require complete native absence evidence from the reviewed verification implementation.')
    expected_paths = sorted(set(settings['expectation']['paths'] +
        [row['disk'] for row in settings['expectation']['guests']] + ['/opt/vms']))
    keys.require(isinstance(evidence['paths'], list) and len(evidence['paths']) == len(expected_paths)
                 and sorted(row.get('path') for row in evidence['paths']) == expected_paths
                 and all(set(row) == {'path', 'exists', 'symlink_ancestor'} and row['exists'] is False
                         and row['symlink_ancestor'] is False for row in evidence['paths'])
                 and isinstance(evidence['blockdevices'], dict) and bool(evidence['blockdevices'].get('blockdevices'))
                 and isinstance(evidence['mounts'], dict) and bool(evidence['mounts'].get('filesystems'))
                 and isinstance(evidence['nftables'], dict) and isinstance(evidence['nftables'].get('nftables'), list)
                 and isinstance(evidence['firewalld_xml'], list) and len(evidence['firewalld_xml']) == 3,
                 'Missing native storage, path or firewall readback cannot establish reset cleanup.')
    if retirement_job is not None:
        keys.require(isinstance(retirement_job, dict)
                     and set(retirement_job) == {'id', 'template_id', 'project_revision'}
                     and all(isinstance(retirement_job[key], int) and not isinstance(retirement_job[key], bool)
                             and retirement_job[key] > 0 for key in ('id', 'template_id'))
                     and retirement_job['project_revision'],
                     'Validate the current running retirement identity before checking proof reuse.')
        inventories = {binding['inventory_id']}
        if source_inventory_id is not None:
            keys.require(isinstance(source_inventory_id, int) and not isinstance(source_inventory_id, bool)
                         and source_inventory_id > 0, 'Retain the exact source ownership inventory.')
            inventories.add(source_inventory_id)
        for inventory_id in sorted(inventories):
            active = client.rows('jobs/?inventory=%s&status__in=new,pending,waiting,running&page_size=200' % inventory_id)
            keys.require(isinstance(active, list) and len(active) <= 256,
                         'Read a bounded complete set of active target jobs before accepting reset evidence.')
            keys.require(not any(row.get('inventory') == inventory_id
                and row.get('status') in ('new', 'pending', 'waiting', 'running')
                and row.get('id') != retirement_job['id'] for row in active),
                'Another target operation is unfinished; preserve ownership until its outcome is known.')
            later = client.rows('jobs/?inventory=%s&id__gt=%s&page_size=200' % (inventory_id, job_id))
            keys.require(isinstance(later, list) and len(later) <= 256,
                         'Read a bounded complete set of later target jobs before accepting reset evidence.')
            for other in later:
                keys.require(isinstance(other, dict) and isinstance(other.get('id'), int)
                             and not isinstance(other['id'], bool), 'Require complete later-job identities.')
                if other['id'] <= job_id or other.get('inventory') != inventory_id or other['id'] == retirement_job['id']:
                    continue
                # A fresh job may reconcile a partially completed prior run of
                # this same metadata-only branch. Any later host/guest work
                # invalidates the old absence observation and needs fresh proof.
                values = other.get('extra_vars')
                values = json.loads(values) if isinstance(values, str) else values
                keys.require(other.get('job_template') == retirement_job['template_id']
                             and other.get('scm_revision') == retirement_job['project_revision']
                             and other.get('status') in ('failed', 'error', 'canceled', 'successful')
                             and isinstance(values, dict)
                             and values.get('aap_post_reset_verification_job') == job_id
                             and values.get('aap_decommission_confirmation') == settings['expectation']['instance_name'],
                             'Later target work invalidated the old reset absence proof; verify the replacement again.')
    return deepcopy(proof)


class FilterModule:
    def filters(self):
        return {}
