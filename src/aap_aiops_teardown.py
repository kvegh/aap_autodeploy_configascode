"""Exact AIOps-only reductions of the existing instance retirement contracts.

Native modules implement API, libvirt and firewall operations. These pure checks
keep that existing lifecycle away from the AAP VM and from other workload owners.
"""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retirement = load('aiops_workload_existing_retirement', ROOT / 'filter_plugins/aap_decommission.py')
keys = load('aiops_workload_existing_keys', ROOT / 'src/aap_instance_keys.py')
codec = load('aiops_workload_existing_yaml', ROOT / 'src/cac_yaml.py')
api_tokens = load('aiops_workload_existing_api_tokens', ROOT / 'src/cac_api_lifecycle.py')
require = keys.require
ROLES = ('zabbix', 'testserver1', 'tra')


def resources(route, zone, related):
    """Select only the three recorded application guests and their publication."""
    result = retirement.resources(route, zone, '/opt/vms', related)
    selected = deepcopy(result)
    selected['scope'] = 'aiops'
    selected['domains'] = [domain for domain in result['domains'] if not domain['primary']]
    selected['dns'] = result['dns'][1:]
    selected['certificates'] = result['certificates'][1:]
    selected['nginx'] = result['nginx'][1:]
    for key in ('disk', 'authority'):
        selected.pop(key)
    require(len(selected['domains']) == 3 and all(not d['primary'] for d in selected['domains'])
            and route['vm_name'] not in [d['name'] for d in selected['domains']]
            and route['aap_hostname'].removeprefix('https://') not in selected['certificates'],
            'AIOps teardown cannot select the base AAP VM, disk, publication or authority.')
    return selected


def identity_key(value):
    return tuple(value[field] for field in ('bridge', 'ipv4', 'mac'))


def only_policy(previous, identities):
    selected = {identity_key(value) for value in identities}
    desired = deepcopy(previous)
    for field in ('https_clients', 'guest_host_clients', 'released_clients', 'http_clients'):
        if field not in desired:
            continue
        retained = [row for row in desired[field] if identity_key(row) not in selected]
        if retained == desired[field]:
            continue
        if retained:
            desired[field] = retained
        else:
            desired.pop(field)
            if not any(desired.get(name) for name in ('https_clients', 'released_clients', 'http_clients')):
                desired.pop('protected_ipv4', None)
    return desired


def rules(policy):
    return {'rule family="ipv4" priority="0" source address="%s/32" '
            'destination address="%s/32" port port="%s" protocol="tcp" accept'
            % (row['ipv4'], destination, port)
            for row in policy.get('guest_host_clients', [])
            for destination in row['destinations'] for port in row['ports']}


def scoped_access(full_plan, route, related, application=None):
    """Narrow a successful full native ownership inspection; never weaken it."""
    require(isinstance(full_plan, dict) and isinstance(related, dict)
            and isinstance(full_plan.get('identities'), list),
            'Inspect existing native ownership before narrowing the AIOps plan.')
    if application is not None and related.get('zabbix'):
        settings = load('aiops_teardown_native_appliance', ROOT / 'src/aap_aiops_settings.py')
        number = int(route['vm_name'].rsplit('-', 1)[1])
        zone = application['aiops_website_dns_zone']
        context = {'instance_name': route['vm_name'], 'instance_number': number, 'version': 'v%02d' % number,
                   'hypervisor': route['hypervisor'], 'zabbix_fqdn': 'zabbix.v%02d.' % number + zone}
        complete = application['aiops_instances'][route['vm_name']]['zabbix']
        settings.zabbix_resource(complete, context, application['aiops_zabbix_source_image']['sha256'])
        require(all(complete.get(field) == value for field, value in related['zabbix'].items()),
                'Native appliance ownership differs from the complete protected API/image provenance.')
    owned = []
    for role in ROLES:
        metadata = related.get(role)
        if not metadata:
            continue
        require(metadata.get('vm_name', role + '-v%02d' % int(route['vm_name'].rsplit('-', 1)[1]))
                == role + '-v%02d' % int(route['vm_name'].rsplit('-', 1)[1])
                and metadata.get('hypervisor_machine_id') == route['hypervisor']['machine_id']
                and metadata.get('verified') is True,
                'Only recorded application guests on this exact hypervisor can be retired.')
        for nic in keys._management.primary_interfaces(metadata, route['hypervisor']):
            value = {'bridge': nic.get('bridge'), 'ipv4': nic.get('address', metadata['address']), 'mac': nic.get('mac')}
            require(value in full_plan['identities'], 'The full native inspection did not prove an AIOps NIC.')
            require(value['ipv4'] != route['vm_ip'], 'An application identity conflicts with the base AAP VM.')
            owned.append(value)
    require(len({identity_key(row) for row in owned}) == len(owned), 'Application NIC identities must be unique.')
    desired = only_policy(full_plan['previous_policy'], owned)
    pin = route['hypervisor']
    require(keys._routing.isolation_policy(pin, desired.get('https_clients', []), desired.get('protected_ipv4'),
            desired.get('guest_host_clients', []), desired.get('released_clients', []), desired.get('http_clients', [])) == desired,
            'The reduced AIOps policy must preserve the complete native schema.')
    result = deepcopy(full_plan)
    result.update(desired_policy=desired, identities=owned, changed=desired != full_plan['previous_policy'],
                  live_primary_identity=None, rich_rules_to_remove=sorted(rules(full_plan['previous_policy']) - rules(desired)),
                  scope='aiops')
    return result


def scoped_reservations(full_plan, route, identities):
    """Keep every AAP reservation and every unrelated native XML field."""
    version = 'v%02d' % int(route['vm_name'].rsplit('-', 1)[1])
    names = {role + '-' + version for role in ROLES}
    result = {'before': deepcopy(full_plan['before']), 'after': deepcopy(full_plan['before']), 'reservations': []}
    for item in full_plan['reservations']:
        node = ET.fromstring(item['xml'])
        node_names = [node.get('name')] if item['kind'] == 'ip-dhcp-host' else [n.text for n in node.findall('hostname')]
        node_names = [name for name in node_names if name]
        matching = [row for row in identities if row['ipv4'] == node.get('ip') and
                    (item['kind'] != 'ip-dhcp-host' or row['mac'] == node.get('mac', '').lower())]
        if not matching:
            continue
        require(len(matching) == 1 and all(name in names for name in node_names),
                'Selected AIOps reservations cannot contain another workload hostname.')
        require(node.get('ip') != route['vm_ip'], 'AIOps cleanup cannot remove an AAP reservation.')
        result['reservations'].append(deepcopy(item))
    for network, scopes in result['after'].items():
        for scope, xml in scopes.items():
            root = ET.fromstring(xml)
            for item in result['reservations']:
                if item['network'] != network or item['scope'] != scope:
                    continue
                expected = retirement.network_shape(item['xml'])
                parents = root.findall('./ip/dhcp' if item['kind'] == 'ip-dhcp-host' else './dns')
                matches = [(parent, node) for parent in parents for node in parent.findall('host')
                           if retirement.network_shape(ET.tostring(node, encoding='unicode')) == expected]
                require(len(matches) == 1, 'Exact preflighted AIOps reservation changed before reduction.')
                matches[0][0].remove(matches[0][1])
            result['after'][network][scope] = ET.tostring(root, encoding='unicode')
    return result


def scoped_context(full_context, access):
    """Retain the existing validated transition shape, removing no AAP rows."""
    require(access.get('scope') == 'aiops' and full_context['previous_policy'] == access['previous_policy'],
            'Narrow only the same completed native retirement inspection.')
    result = deepcopy(full_context)
    result['guests'] = [row for row in result['guests'] if row['role'] in ROLES]
    result['identities'] = deepcopy(access['identities'])
    result['desired_policy'] = deepcopy(access['desired_policy'])
    result['removed_rules'] = rules(result['previous_policy']) - rules(result['desired_policy'])
    require(len(result['guests']) == 3 and not any(row['role'] == 'aap' for row in result['guests']),
            'AIOps publication cannot remove primary AAP ownership.')
    return result


def documents_without_instance(capture, runtime, selected, expected_profile):
    """Remove paired selected namespace last; shared inputs and history survive."""
    require(isinstance(selected, str) and re.fullmatch(r'aap27-test-[1-9][0-9]*', selected)
            and capture.get('cac_import_metadata', {}).get('project_id') == 'aiops-selfhealing-demo'
            and isinstance(capture.get('aiops_instances'), dict)
            and runtime.get('schema_version') == 1 and isinstance(runtime.get('instances'), dict),
            'Retire only paired namespaces in the maintained AIOps capture and runtime.')
    profile, settings = capture['aiops_instances'].get(selected), runtime['instances'].get(selected)
    require((profile is None) == (settings is None), 'Selected profile and runtime presence must agree.')
    require(profile is None or profile == expected_profile, 'Selected AIOps ownership changed after preflight.')
    desired, next_runtime = deepcopy(capture), deepcopy(runtime)
    desired['aiops_instances'].pop(selected, None)
    next_runtime['instances'].pop(selected, None)
    return desired, next_runtime


def require_quiescent(controller_jobs, activations, activation_instances):
    require(all(row.get('status') in ('successful', 'failed', 'error', 'canceled') for row in controller_jobs),
            'Wait for existing AIOps jobs to finish; teardown never cancels user work.')
    require(all(row.get('is_enabled') is False for row in activations), 'Disable selected EDA delivery before teardown.')
    require(all(row.get('status') in ('stopped', 'completed', 'failed', 'error') for row in activation_instances),
            'Wait for selected EDA workers to stop before teardown.')
    return True


def publication_context(configuration, shared, allocation, client, selected, pin, application, transition=None):
    """Use the normal registry/API proof while retaining its consumed AAP owner."""
    pin = keys._routing.hypervisor_pin(pin)
    records = [row for row in allocation['aap_vm_allocation']['reservations'].values() if row.get('vm_name') == selected]
    require(len(records) == 1 and records[0].get('decommissioned', False) is False,
            'A workload reset requires one active existing AAP allocation.')
    record = records[0]
    route = keys._routing.instance_route(record['instance_route'])
    require(route['hypervisor'] == pin, 'A workload reset cannot change its owning hypervisor.')
    proof = keys.source_related_resources(client, shared, allocation['aap_vm_allocation'], selected, application)
    related = proof['related_resources']
    recovery = [row for row in configuration['autodeploy_configuration']['inventories']
                if keys.inventory_variables(row).get('aap_hypervisor_pin') == pin]
    require(len(recovery) == 1, 'Resolve the existing canonical rebuild inventory.')
    values = keys.inventory_variables(recovery[0])
    current = keys._routing.isolation_policy(pin, values.get('aap_hypervisor_isolation_https_clients', []),
        values.get('aap_hypervisor_isolation_protected_ipv4', []), values.get('aap_hypervisor_isolation_host_clients', []),
        values.get('aap_hypervisor_isolation_released_clients', []), values.get('aap_hypervisor_isolation_http_clients', []))
    if transition is None:
        previous = current
    else:
        require(isinstance(transition, dict) and set(transition) == {
            'previous_policy', 'desired_policy', 'identities', 'related_resources'}
            and transition['related_resources'] == related
            and current in (transition['previous_policy'], transition['desired_policy']),
            'AIOps ownership or canonical policy changed after this reset preflight.')
        previous = transition['previous_policy']
    # The full existing validator proves every native resource and retained AAP
    # before the projection below excludes AAP from all writable destinations.
    all_resources = dict(record.get('instance_resources', {}), **related)
    identities = []
    for role, metadata in all_resources.items():
        require(role in ('aap',) + ROLES, 'Unknown resource ownership requires review.')
        for nic in keys._management.primary_interfaces(metadata, pin):
            identities.append({'bridge': nic['bridge'], 'ipv4': nic.get('address', metadata['address']), 'mac': nic['mac']})
    full = keys.isolation_retirement_context(record, selected, route['aap_hostname'], {
        'previous_policy': previous, 'desired_policy': only_policy(previous, identities), 'identities': identities}, related)
    access = scoped_access({'previous_policy': previous, 'identities': identities}, route, related, application)
    context = scoped_context(full, access)
    if transition is not None:
        require(context['desired_policy'] == transition['desired_policy'] and context['identities'] == transition['identities'],
                'Publish exactly the native preflighted AIOps-only policy reduction.')
    keys.verify_remaining_guest_grants(context['desired_policy'], proof)
    context['related_resources'] = deepcopy(related)
    context['reservation'] = deepcopy(record)
    return context


def publication_transition(context):
    return {field: deepcopy(context[field]) for field in ('previous_policy', 'desired_policy', 'identities', 'related_resources')}


TARGET_KINDS = (
    ('eda_rulebook_activations', '/api/eda/v1/activations/'),
    ('controller_templates', '/api/controller/v2/job_templates/'),
    ('eda_event_streams', '/api/eda/v1/event-streams/'),
    ('controller_hosts', '/api/controller/v2/hosts/'),
    ('controller_inventories', '/api/controller/v2/inventories/'),
    ('eda_projects', '/api/eda/v1/projects/'),
    ('controller_projects', '/api/controller/v2/projects/'),
    ('eda_decision_environments', '/api/eda/v1/decision-environments/'),
    ('controller_execution_environments', '/api/controller/v2/execution_environments/'),
    ('eda_credentials', '/api/eda/v1/eda-credentials/'),
    ('controller_credentials', '/api/controller/v2/credentials/'),
    ('aap_applications', '/api/gateway/v1/applications/'),
    ('controller_labels', '/api/controller/v2/labels/'),
)


def native_identity(row):
    """Stable native ownership fields; omit API secrets and changing job status."""
    fields = ('id', 'name', 'organization', 'inventory', 'project', 'playbook', 'scm_type', 'scm_url',
              'scm_branch', 'image', 'credential_type', 'decision_environment', 'rulebook_name',
              'authorization_grant_type', 'client_type', 'url', 'user', 'credential', 'execution_environment', 'image_url', 'event_stream_type', 'description')
    result = {field: deepcopy(row[field]) for field in fields if field in row}
    for field in ('organization', 'inventory', 'project', 'credential_type', 'decision_environment', 'credential', 'user'):
        if isinstance(result.get(field), dict):
            result[field] = {key: result[field][key] for key in ('id', 'name') if key in result[field]}
    return result


def relation_name(row, field, client=None, kind=None):
    summary = row.get('summary_fields', {}).get(field)
    if isinstance(summary, dict):
        return summary.get('name')
    value = row.get(field)
    if isinstance(value, dict) and isinstance(value.get('name'), str):
        return value['name']
    if isinstance(value, str):
        return value
    identity = value.get('id') if isinstance(value, dict) else value
    if identity is None:
        identity = row.get(field + '_id')
    if client is not None and type(identity) is int and identity > 0:
        if field == 'organization':
            endpoint = '/api/gateway/v1/organizations/' if kind == 'aap_applications' else '/api/eda/v1/organizations/' if kind.startswith('eda_') else '/api/controller/v2/organizations/'
        elif field == 'project':
            endpoint = '/api/eda/v1/projects/' if kind.startswith('eda_') else '/api/controller/v2/projects/'
        elif field == 'credential_type':
            endpoint = '/api/eda/v1/credential-types/' if kind.startswith('eda_') else '/api/controller/v2/credential_types/'
        else:
            endpoint = {'inventory': '/api/controller/v2/inventories/', 'decision_environment': '/api/eda/v1/decision-environments/'}[field]
        return client.request('GET', endpoint + str(identity) + '/').get('name')
    return None


def workflow_references_absent(client, inventories, credentials):
    """AIOps owns no workflows: preserve all foreign workflow dependencies."""
    for endpoint in ('workflow_job_templates', 'workflow_job_template_nodes'):
        rows = client.rows('/api/controller/v2/' + endpoint + '/?page_size=200')
        require(len(rows) <= 200, 'Require bounded complete workflow relationships.')
        for row in rows:
            require(type(row.get('id')) is int, 'Require native workflow identities.')
            inventory = row.get('inventory')
            inventory = inventory.get('id') if isinstance(inventory, dict) else inventory
            require(inventory not in inventories, 'A foreign workflow uses the selected AIOps inventory.')
            require(row.get('webhook_credential') not in credentials,
                    'A foreign workflow uses a selected AIOps webhook credential.')
            if endpoint == 'workflow_job_template_nodes':
                attached = client.rows('/api/controller/v2/' + endpoint + '/%d/credentials/?page_size=200' % row['id'])
                require(not {value['id'] for value in attached} & set(credentials),
                        'A foreign workflow node uses selected AIOps credentials.')


def application_tokens_absent(client, application_ids):
    # The existing EDA service token is explicitly application=None in the
    # normal lifecycle. No application-attached token has owned provenance.
    for identity in application_ids:
        require(not client.rows('/api/gateway/v1/applications/%d/tokens/?page_size=200' % identity),
                'Application tokens lack selected workload ownership; preserve the application for review.')


def selected_target_plan(client, definitions, required_label, retained_tokens=None):
    """Resolve real IDs and refuse collisions or cross-project references first."""
    require(isinstance(definitions, dict) and required_label == 'aiops_selfhealing',
            'Use only the normally rendered reviewed AIOps resource definitions.')
    allowed = {kind for kind, _ in TARGET_KINDS}
    require(not any(value for kind, value in definitions.items() if kind not in allowed),
            'Unexpected resource kinds need an explicit workload cleanup contract.')
    lists, picked = {}, {}
    for kind, endpoint in TARGET_KINDS:
        declared = definitions.get(kind, [])
        require(isinstance(declared, list) and len(declared) <= 64
                and all(isinstance(row, dict) and isinstance(row.get('name'), str) and row['name'] for row in declared)
                and len({row['name'] for row in declared}) == len(declared),
                'Use complete unique bounded AIOps definitions.')
        # Read complete visible lists, not name-only discovery that could hide
        # another project using a resource which is about to be removed.
        rows = client.rows(endpoint + '?page_size=200')
        require(len(rows) <= 200 and all(isinstance(row, dict) and type(row.get('id')) is int and row['id'] > 0 for row in rows),
                'Require complete bounded native resources before planning deletion.')
        lists[kind] = rows
        chosen = []
        for expected in declared:
            matches = [row for row in rows if row.get('name') == expected['name']]
            require(len(matches) <= 1, 'AIOps object names are ambiguous; no deletion was planned.')
            if not matches:
                continue
            row = matches[0]
            for field in ('organization', 'inventory', 'project', 'credential_type', 'decision_environment'):
                if field in expected:
                    require(relation_name(row, field, client, kind) == expected[field],
                            'An AIOps native relationship differs from its reviewed definition.')
            for field in ('playbook', 'scm_type', 'scm_url', 'scm_branch', 'image', 'image_url', 'url', 'event_stream_type', 'authorization_grant_type', 'client_type'):
                if field in expected:
                    require(row.get(field) == expected[field], 'An AIOps native object has conflicting ownership fields.')
            if kind == 'eda_rulebook_activations' and 'rulebook' in expected:
                require(row.get('rulebook_name') == expected['rulebook'], 'An EDA activation uses a different rulebook.')
            if kind == 'controller_templates':
                labels = client.rows(endpoint + '%d/labels/?page_size=200' % row['id'])
                require({label.get('name') for label in labels} == {required_label},
                        'The selected job template must retain its exact AIOps ownership label.')
                schedules = client.rows(endpoint + '%d/schedules/?page_size=200' % row['id'])
                references = client.rows('/api/controller/v2/workflow_job_template_nodes/?unified_job_template=%d&page_size=200' % row['id'])
                require(not schedules and not references,
                        'Unexpected schedules or workflow references must be resolved before teardown.')
            if kind == 'controller_hosts':
                require(keys.inventory_variables(row) == keys.inventory_variables({'variables': expected.get('variables', {})}),
                        'The native inventory host changed from its selected AIOps configuration.')
            chosen.append(row)
        picked[kind] = chosen
    ids = {kind: {row['id'] for row in rows} for kind, rows in picked.items()}
    workflow_references_absent(client, ids['controller_inventories'], ids['controller_credentials'])
    application_tokens_absent(client, ids['aap_applications'])
    # Do not infer that an object is exclusive just because its name matches.
    # Native relationships outside the selected graph stop before any disable,
    # deletion, VM power action or external state publication.
    for row in lists['controller_templates']:
        if row['id'] in ids['controller_templates']:
            continue
        require(row.get('inventory') not in ids['controller_inventories']
                and row.get('project') not in ids['controller_projects']
                and row.get('execution_environment') not in ids['controller_execution_environments'],
                'Another Controller template uses selected AIOps infrastructure; preserve it for review.')
        credentials = client.rows('/api/controller/v2/job_templates/%d/credentials/?page_size=200' % row['id'])
        labels = client.rows('/api/controller/v2/job_templates/%d/labels/?page_size=200' % row['id'])
        require(not ({value['id'] for value in credentials} & ids['controller_credentials'])
                and not ({value['id'] for value in labels} & ids['controller_labels']),
                'Another Controller template uses selected AIOps credentials or labels.')
    for row in lists['controller_hosts']:
        require(row['id'] in ids['controller_hosts'] or row.get('inventory') not in ids['controller_inventories'],
                'The AIOps inventory contains an unreviewed host; preserve it for review.')
    for row in lists['controller_projects']:
        require(row['id'] in ids['controller_projects'] or row.get('credential') not in ids['controller_credentials'],
                'Another project uses a selected AIOps credential.')
    for row in lists['controller_execution_environments']:
        require(row['id'] in ids['controller_execution_environments'] or row.get('credential') not in ids['controller_credentials'],
                'Another execution environment uses a selected AIOps credential.')
    for row in lists['eda_rulebook_activations']:
        if row['id'] in ids['eda_rulebook_activations']:
            continue
        for field, kind in [('project', 'eda_projects'), ('decision_environment', 'eda_decision_environments')]:
            value = row.get(field)
            value = value.get('id') if isinstance(value, dict) else value
            require(value not in ids[kind], 'Another EDA activation uses selected AIOps infrastructure.')
        for field, kind in [('event_streams', 'eda_event_streams'), ('eda_credentials', 'eda_credentials')]:
            values = row.get(field, [])
            require(isinstance(values, list), 'Read complete native EDA relationships before teardown.')
            used = {v.get('id') if isinstance(v, dict) else v for v in values}
            require(not used & ids[kind], 'Another EDA activation uses a selected AIOps stream or credential.')
    for row in lists['eda_event_streams']:
        credential = row.get('eda_credential')
        credential = credential.get('id') if isinstance(credential, dict) else credential
        require(row['id'] in ids['eda_event_streams'] or credential not in ids['eda_credentials'],
                'Another EDA stream uses a selected AIOps credential.')
    for row in lists['eda_decision_environments']:
        credential = row.get('credential')
        credential = credential.get('id') if isinstance(credential, dict) else credential
        require(row['id'] in ids['eda_decision_environments'] or credential not in ids['eda_credentials'],
                'Another EDA decision environment uses a selected AIOps registry credential.')
    operations = [{'kind': kind, 'endpoint': endpoint, 'identity': native_identity(row)}
                  for kind, endpoint in TARGET_KINDS for row in picked[kind]]
    access_tokens = selected_access_tokens(client, picked['eda_credentials'], definitions.get('eda_credentials', []), retained_tokens or [])
    return {'operations': operations, 'access_tokens': access_tokens, 'selected_ids': {kind: sorted(values) for kind, values in ids.items()},
            'required_label': required_label}


def active_target_jobs(client, plan):
    ids = plan['selected_ids']['controller_templates']
    if not ids:
        return []
    return client.rows('/api/controller/v2/jobs/?status__in=new,pending,waiting,running&job_template__in=' +
                       ','.join(str(value) for value in ids) + '&page_size=200')


def quiesce_target(client, plan, apply=False):
    """Disable owned EDA definitions; never cancel any Controller job."""
    activations = []
    changed = False
    for operation in plan['operations']:
        if operation['kind'] != 'eda_rulebook_activations':
            continue
        path = operation['endpoint'] + str(operation['identity']['id']) + '/'
        row = client.request('GET', path)
        require(native_identity(row) == operation['identity'], 'An activation changed since the ownership plan.')
        require(type(row.get('is_enabled')) is bool and 'current_job_id' in row,
                'Read the actual enabled and worker state before stopping selected delivery.')
        if row['is_enabled'] and apply:
            client.request('POST', path + 'disable/', {})
            changed = True
            row = client.request('GET', path)
        activations.append(row)
    jobs = active_target_jobs(client, plan)
    ready = not jobs and all(row['is_enabled'] is False and row['current_job_id'] is None for row in activations)
    return {'changed': changed,
            'quiescent': ready, 'active_job_ids': [row['id'] for row in jobs],
            'pending_activation_ids': [row['id'] for row in activations if row['is_enabled'] or row['current_job_id'] is not None]}


def remove_target(client, plan):
    """Recheck IDs and immutable relationships immediately before each delete."""
    require(quiesce_target(client, plan)['quiescent'], 'Selected workers must be stopped and jobs complete before removal.')
    changed = False
    for operation in plan['operations']:
        identity, endpoint = operation['identity'], operation['endpoint']
        rows = client.rows(endpoint + '?name=' + keys.quote(identity['name']) + '&page_size=200')
        require(len(rows) <= 1, 'The preflighted selected object became ambiguous.')
        if not rows:
            continue
        require(native_identity(rows[0]) == identity, 'A selected object changed before deletion; preserve it for review.')
        require(not active_target_jobs(client, plan), 'New selected jobs appeared; teardown will not cancel them.')
        no_new_references(client, operation, plan)
        client.request('DELETE', endpoint + str(identity['id']) + '/')
        require(not client.rows(endpoint + '?name=' + keys.quote(identity['name']) + '&page_size=200'),
                'Selected AIOps object deletion was not verified.')
        changed = True
    return changed


def authority_absent(result, hostname, zone, server):
    """Accept only direct authoritative NXDOMAIN or NODATA with the zone SOA."""
    from ipaddress import IPv4Address
    if (not isinstance(result, dict) or type(result.get('rc')) is not int or result['rc'] != 0
            or result.get('failed') is True or not isinstance(result.get('stdout'), str)):
        return False
    dns = load('aiops_teardown_dns_names', ROOT / 'filter_plugins/godaddy_v3.py')
    try:
        hostname, zone = dns._dns_name(hostname), dns._dns_name(zone)
        if not hostname.endswith('.' + zone):
            return False
        text = result['stdout']
        headers = re.findall(r'^;; ->>HEADER<<- opcode: (\w+), status: (\w+), id: \d+\s*$', text, re.M)
        flags = re.findall(r'^;; flags: ([a-z ]*); QUERY: (\d+), ANSWER: (\d+), AUTHORITY: (\d+), ADDITIONAL: \d+\s*$', text, re.M)
        questions = re.findall(r'^;([^;\s]+)\s+IN\s+(\w+)\s*$', text, re.M)
        servers = re.findall(r'^;; SERVER: ([0-9.]+)#53(?:\([^)]*\))?.*$', text, re.M)
        if (len(headers) != 1 or headers[0][0] != 'QUERY' or headers[0][1] not in ('NXDOMAIN', 'NOERROR')
                or len(flags) != 1 or len(questions) != 1 or questions[0][1] != 'A'
                or dns._dns_name(questions[0][0]) != hostname or servers != [str(IPv4Address(server))]):
            return False
        tokens, question_count, answer_count, authority_count = flags[0]
        if (not {'qr', 'aa'} <= set(tokens.split()) or {'rd', 'tc'} & set(tokens.split())
                or (question_count, answer_count, authority_count) != ('1', '0', '1')):
            return False
        authority, answer, section = [], [], None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(';;'):
                section = 'authority' if line == ';; AUTHORITY SECTION:' else 'answer' if line == ';; ANSWER SECTION:' else None
                continue
            if not line or line.startswith(';'):
                continue
            if section == 'authority':
                authority.append(line)
            elif section == 'answer':
                answer.append(line)
            else:
                return False
        if answer or len(authority) != 1:
            return False
        fields = authority[0].split()
        return (len(fields) == 11 and dns._dns_name(fields[0]) == zone and fields[1].isdigit()
                and 0 <= int(fields[1]) <= 2 ** 31 - 1 and fields[2:4] == ['IN', 'SOA']
                and bool(dns._dns_name(fields[4])) and bool(dns._dns_name(fields[5]))
                and all(field.isdigit() and 0 <= int(field) <= 2 ** 32 - 1 for field in fields[6:]))
    except Exception:
        # Filter/shape errors never establish record absence.
        return False


def authority_absent_round(results, endpoints, hostname, zone):
    require(isinstance(results, list) and isinstance(endpoints, list) and 1 <= len(endpoints) <= 32
            and len(results) == len(endpoints), 'Require one complete bounded authoritative absence round.')
    passed = []
    for result, endpoint in zip(results, endpoints):
        require(result.get('item') == endpoint, 'An absence observation came from an unexpected endpoint.')
        passed.append(authority_absent(result, hostname, zone, endpoint['address']))
    return {'ready': all(passed), 'authority_count': len(endpoints), 'ready_count': sum(passed)}


def subscription_absence_valid(profile, selected):
    """A removed TRA keeps its exact unregistration proof until final retirement."""
    if (not isinstance(profile, dict) or not isinstance(profile.get('teardown', {}), dict)
            or not set(profile.get('teardown', {})) <= {'subscription_absence', 'target_access_tokens'}):
        return False
    tra = profile.get('tra')
    if not tra or set(tra) == {'configuration'}:
        return 'subscription_absence' not in profile.get('teardown', {})
    receipt = profile.get('teardown', {}).get('subscription_absence')
    fields = {'instance_name', 'guest_name', 'uuid', 'machine_id', 'registration_absent',
              'consumer_certificate_absent', 'consumer_uuid', 'target_job', 'source_job_id', 'source_project_revision'}
    return (isinstance(receipt, dict) and set(receipt) == fields
            and receipt['instance_name'] == selected and receipt['guest_name'] == tra.get('vm_name')
            and receipt['uuid'] == tra.get('uuid') and receipt['machine_id'] == tra.get('machine_id')
            and receipt['registration_absent'] is True and receipt['consumer_certificate_absent'] is True
            and (receipt['consumer_uuid'] is None or (isinstance(receipt['consumer_uuid'], str)
                and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', receipt['consumer_uuid'])))
            and isinstance(receipt['target_job'], dict) and set(receipt['target_job']) == {'id', 'template_id', 'scm_revision'}
            and isinstance(receipt['target_job']['id'], int) and not isinstance(receipt['target_job']['id'], bool) and receipt['target_job']['id'] > 0
            and isinstance(receipt['target_job']['template_id'], int) and not isinstance(receipt['target_job']['template_id'], bool) and receipt['target_job']['template_id'] > 0
            and isinstance(receipt['target_job']['scm_revision'], str)
            and re.fullmatch(r'[0-9a-f]{40}', receipt['target_job']['scm_revision'])
            and isinstance(receipt['source_job_id'], str) and re.fullmatch(r'[1-9][0-9]*', receipt['source_job_id'])
            and isinstance(receipt['source_project_revision'], str)
            and re.fullmatch(r'[0-9a-f]{40}', receipt['source_project_revision']))


def record_subscription_absence(capture, selected, proof, job_id, revision):
    result = deepcopy(capture)
    require(selected in result['aiops_instances'], 'Retain the selected owner while recording subscription absence.')
    profile = result['aiops_instances'][selected]
    require(isinstance(profile, dict) and isinstance(profile.get('tra'), dict), 'Prove the selected TRA before removing registration.')
    require(isinstance(proof, dict) and proof.get('source_job_id') == str(job_id)
            and proof.get('source_project_revision') == revision,
            'Use only this running Source job\'s fresh subscription absence proof.')
    require(isinstance(profile.get('teardown', {}), dict)
            and set(profile.get('teardown', {})) <= {'subscription_absence', 'target_access_tokens'},
            'Unknown teardown owner state requires review.')
    profile.setdefault('teardown', {})['subscription_absence'] = deepcopy(proof)
    require(subscription_absence_valid(profile, selected),
            'RHSM absence must match the exact selected TRA UUID and authenticated machine identity.')
    return result


def publications_owned(text, plan):
    """Reject renamed/shared vhosts or certificate references before unlinking."""
    require(isinstance(text, str) and plan.get('scope') == 'aiops', 'Inspect nginx complete native configuration first.')
    sections = re.split(r'^# configuration file ([^\n]+):\s*$', text, flags=re.M)
    require(len(sections) >= 3, 'nginx did not return complete native configuration sections.')
    files = {sections[index]: sections[index + 1] for index in range(1, len(sections), 2)}
    require(len(files) == (len(sections) - 1) // 2, 'Duplicate nginx source sections require review.')
    for path, hostname, role in zip(plan['nginx'], plan['certificates'], ('website', 'monitoring frontend')):
        if path not in files:
            continue
        content = files[path].lstrip()
        require(content.startswith('# Managed by the AIOps ' + role + ' playbook for ' + hostname + '.'),
                'A selected virtual host has no exact AIOps ownership marker.')
        names = [name for row in re.findall(r'^\s*server_name\s+([^;]+);\s*$', content, re.M) for name in row.split()]
        require(names and set(names) == {hostname}, 'A selected virtual host also serves another name.')
    for path, content in files.items():
        if path in plan['nginx']:
            continue
        references = plan['nginx'] + plan['website_paths'] + ['/etc/letsencrypt/live/' + hostname + '/' for hostname in plan['certificates']]
        require(not any(value in content for value in references)
                and ('redhat_' + plan['version'] + '_panic') not in content,
                'An unrelated nginx configuration uses selected publication resources; preserve them for review.')
    return True


def no_new_references(client, operation, plan):
    """Recheck direct foreign consumers immediately before each dependent delete."""
    kind, identity = operation['kind'], operation['identity']['id']
    selected = plan['selected_ids']
    if kind in ('controller_inventories', 'controller_credentials'):
        workflow_references_absent(client, selected['controller_inventories'], selected['controller_credentials'])
    if kind == 'aap_applications':
        application_tokens_absent(client, [identity])
    if kind == 'controller_templates':
        references = client.rows('/api/controller/v2/workflow_job_template_nodes/?unified_job_template=%d&page_size=200' % identity)
        schedules = client.rows('/api/controller/v2/job_templates/%d/schedules/?page_size=200' % identity)
        require(not references and not schedules, 'A workflow or schedule reference appeared after preflight.')
    if kind == 'controller_projects':
        project = client.request('GET', '/api/controller/v2/projects/%d/' % identity)
        require(project.get('current_job') is None, 'A selected project update is still running; wait for its actual outcome.')
    relation = {'controller_projects': 'project', 'controller_inventories': 'inventory',
                'controller_execution_environments': 'execution_environment', 'controller_labels': 'labels',
                'controller_credentials': 'credentials'}.get(kind)
    if relation:
        templates = client.rows('/api/controller/v2/job_templates/?%s=%d&page_size=200' % (relation, identity))
        require(all(row['id'] in selected['controller_templates'] for row in templates),
                'A foreign Controller reference appeared after preflight; preserve the selected dependency.')
    if kind == 'controller_inventories':
        hosts = client.rows('/api/controller/v2/hosts/?inventory=%d&page_size=200' % identity)
        require(all(row['id'] in selected['controller_hosts'] for row in hosts),
                'An unreviewed host appeared in the selected inventory.')
        sources = client.rows('/api/controller/v2/inventory_sources/?inventory=%d&page_size=200' % identity)
        require(not sources, 'An unreviewed inventory source uses the selected inventory.')
    if kind == 'controller_credentials':
        for endpoint, target_kind in [('projects', 'controller_projects'), ('execution_environments', 'controller_execution_environments')]:
            rows = client.rows('/api/controller/v2/%s/?credential=%d&page_size=200' % (endpoint, identity))
            require(all(row['id'] in selected[target_kind] for row in rows),
                    'A foreign registry or SCM credential reference appeared after preflight.')
    if kind == 'eda_credentials':
        for endpoint, target_kind, field in [('/api/eda/v1/event-streams/', 'eda_event_streams', 'eda_credential'),
                                              ('/api/eda/v1/decision-environments/', 'eda_decision_environments', 'credential')]:
            for row in client.rows(endpoint + '?page_size=200'):
                reference = row.get(field)
                reference = reference.get('id') if isinstance(reference, dict) else reference
                require(row['id'] in selected[target_kind] or reference != identity,
                        'A foreign EDA stream or environment credential reference appeared after preflight.')
    if kind in ('eda_projects', 'eda_decision_environments', 'eda_credentials', 'eda_event_streams'):
        activations = client.rows('/api/eda/v1/activations/?page_size=200')
        field = {'eda_projects': 'project', 'eda_decision_environments': 'decision_environment',
                 'eda_credentials': 'eda_credentials', 'eda_event_streams': 'event_streams'}[kind]
        for row in activations:
            if row['id'] in selected['eda_rulebook_activations']:
                continue
            values = row.get(field, [])
            values = values if isinstance(values, list) else [values]
            used = {value.get('id') if isinstance(value, dict) else value for value in values}
            require(identity not in used, 'A foreign EDA reference appeared after preflight.')


def selected_dns_tokens(capture, runtime, selected):
    """An active owner must retain its selected encrypted credential namespace."""
    require(isinstance(capture, dict) and isinstance(runtime, dict)
            and runtime.get('schema_version') == 1 and isinstance(runtime.get('instances'), dict),
            'Require the existing selected runtime schema before DNS teardown.')
    owned = selected in capture.get('aiops_instances', {})
    if owned:
        settings = runtime['instances'].get(selected)
        require(isinstance(settings, dict), 'The active owner has no selected runtime; preserve DNS for review.')
    else:
        require(selected not in runtime['instances'], 'A runtime survives its absent owner; preserve it for review.')
        settings = capture
    names = ('demo_website_dns_api_token', 'demo_zabbix_dns_api_token')
    require(all(isinstance(settings.get(name), str) and settings[name].strip()
                and '\n' not in settings[name] and '\r' not in settings[name] for name in names),
            'Require the exact selected DNS credentials; never fall back for an active owner.')
    return {name: settings[name] for name in names}


def verified_subscription_artifact(job, template, project, profile, selected, identity, source_job_id, source_revision):
    """Bind a real completed normal child job to this selected native TRA."""
    require(job.get('id') == identity and job.get('job_template') == template['id']
            and job.get('project') == template['project'] and job.get('inventory') == template['inventory']
            and job.get('playbook') == 'playbooks/retire_tra_subscription.yml' and job.get('limit') == 'tra'
            and job.get('status') == 'successful' and job.get('failed') is False
            and job.get('event_processing_finished') is True,
            'The exact target-local retirement job must finish successfully before disk deletion.')
    require(project.get('id') == template['project'] and job.get('scm_revision') == project.get('scm_revision')
            and isinstance(job.get('scm_revision'), str) and bool(re.fullmatch('[0-9a-f]{40}', job['scm_revision'])),
            'Verify the actual current project revision used by subscription retirement.')
    proof = job.get('artifacts', {}).get('aap_aiops_subscription_absence')
    require(isinstance(proof, dict) and proof.get('target_job_id') == str(identity)
            and proof.get('target_job_template_id') == str(template['id'])
            and proof.get('target_project_revision') == job['scm_revision'],
            'Retain the actual native target job artifact, never an inferred unregistration result.')
    tra = profile.get('tra', {})
    require(proof.get('instance_name') == selected and proof.get('guest_name') == tra.get('vm_name')
            and proof.get('uuid') == tra.get('uuid') and proof.get('machine_id') == tra.get('machine_id')
            and proof.get('registration_absent') is True and proof.get('consumer_certificate_absent') is True
            and (proof.get('consumer_uuid') is None or isinstance(proof.get('consumer_uuid'), str)
                 and bool(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', proof['consumer_uuid']))),
            'Native unregistration evidence must belong to the same exact selected TRA.')
    normalized = {field: deepcopy(proof[field]) for field in ('instance_name', 'guest_name', 'uuid', 'machine_id',
                  'registration_absent', 'consumer_certificate_absent', 'consumer_uuid')}
    normalized.update(source_job_id=str(source_job_id), source_project_revision=source_revision,
                      target_job={'id': identity, 'template_id': template['id'], 'scm_revision': job['scm_revision']})
    return normalized


def access_expected(receipt):
    require(isinstance(receipt, dict) and set(receipt) == {'schema_version', 'credential_name', 'organization',
            'credential_type', 'host', 'token_id', 'user_id', 'description', 'base_description'}
            and isinstance(receipt['schema_version'], int) and not isinstance(receipt['schema_version'], bool)
            and receipt['schema_version'] == 1,
            'Require the exact persisted native EDA token receipt schema.')
    return {'name': receipt['credential_name'], 'organization': receipt['organization'],
            'credential_type': receipt['credential_type'], 'description': receipt['base_description'],
            'inputs': {'host': receipt['host']}}


def access_credential_matches(row, expected):
    actual = row.get('inputs', {})
    require(isinstance(actual, dict) and actual.get('oauth_token')
            and actual.get('host', '').rstrip('/') == expected['inputs']['host'].rstrip('/')
            and {key: value for key, value in actual.items() if key not in ('host', 'oauth_token')} ==
                {key: value for key, value in expected['inputs'].items() if key not in ('host', 'oauth_token')},
            'The native EDA access credential changed; preserve token ownership for review.')
    return True


def selected_access_tokens(client, native_credentials, definitions, retained):
    """Recover only native first-creation receipts or their retained owner copy."""
    require(isinstance(retained, list) and len(retained) <= 4, 'Keep bounded exact workload token receipts.')
    saved = {}
    for receipt in retained:
        expected = access_expected(receipt)
        require(receipt['credential_name'] not in saved
                and api_tokens.eda_token_receipt(receipt['description'], expected, client.hostname) == receipt,
                'Retained token ownership changed or belongs to another target.')
        saved[receipt['credential_name']] = receipt
    planned = []
    names = set()
    for expected in definitions:
        if expected.get('credential_type') != 'Red Hat Ansible Automation Platform':
            continue
        names.add(expected['name'])
        require(expected.get('inputs', {}).get('host', '').rstrip('/') == client.hostname + '/api/controller',
                'The selected EDA access must target this exact receiving AAP.')
        rows = [row for row in native_credentials if row.get('name') == expected['name']]
        require(len(rows) <= 1, 'The selected EDA token credential is ambiguous.')
        receipt = saved.get(expected['name'])
        if rows:
            access_credential_matches(rows[0], expected)
            owned = api_tokens.eda_owned_token(client, rows[0].get('description', ''), expected, allow_absent=True)
            require(owned is not None, 'Legacy EDA access has no token receipt; recover original native evidence before teardown.')
            require(receipt is None or receipt == owned['receipt'], 'Native and retained EDA token receipts differ.')
            receipt = owned['receipt']
        elif receipt is not None:
            owned = api_tokens.eda_owned_token(client, receipt['description'], expected, allow_absent=True)
        else:
            # Absence evidence may refuse a lost token, but never grants deletion
            # ownership merely from its human-readable description.
            rows = client.rows('/api/gateway/v1/tokens/?page_size=200')
            require(len(rows) <= 200 and not any(row.get('description') == 'CaC EDA Controller access: ' + expected['name'] for row in rows),
                    'An unreceipted EDA token remains; preserve it and recover original native evidence.')
            continue
        planned.append({'receipt': receipt, 'expected': deepcopy(expected), 'credential_id': rows[0]['id'] if rows else None,
                        'token_preimage': owned['token']})
    require(set(saved) <= names, 'Retained tokens refer to an undeclared credential; preserve ownership for review.')
    require(len({item['receipt']['token_id'] for item in planned}) == len(planned), 'Do not share token ownership across credentials.')
    return planned


def access_tokens_absent(client, plan):
    for item in plan.get('access_tokens', []):
        owned = api_tokens.eda_owned_token(client, item['receipt']['description'], item['expected'], allow_absent=True)
        require(owned is not None and owned['receipt'] == item['receipt'] and owned['token'] is None,
                'The exact owned EDA token remains; retain workload ownership.')
    return True


def record_target_access(capture, selected, plan):
    result = deepcopy(capture)
    profile = result['aiops_instances'].get(selected)
    require(isinstance(profile, dict) and isinstance(profile.get('teardown', {}), dict)
            and set(profile.get('teardown', {})) <= {'subscription_absence', 'target_access_tokens'},
            'Keep known native workload teardown ownership only.')
    desired = [deepcopy(item['receipt']) for item in plan.get('access_tokens', [])]
    for receipt in desired:
        access_expected(receipt)
    previous = profile.get('teardown', {}).get('target_access_tokens')
    require(('target_access_tokens' not in profile.get('teardown', {}) or isinstance(previous, list))
            and (previous is None or previous == desired), 'Persisted native token ownership changed; preserve it for review.')
    profile.setdefault('teardown', {})['target_access_tokens'] = desired
    return result


def revoke_target_access(client, plan, protected_ids=()):
    changed = False
    for item in plan.get('access_tokens', []):
        if item['credential_id'] is not None:
            operation = next((row for row in plan['operations'] if row['kind'] == 'eda_credentials'
                              and row['identity']['id'] == item['credential_id']), None)
            require(operation is not None, 'Use only the preflighted native EDA credential owner.')
            current = client.request('GET', operation['endpoint'] + str(item['credential_id']) + '/')
            require(native_identity(current) == operation['identity'], 'The native EDA token owner changed after planning.')
            access_credential_matches(current, item['expected'])
            no_new_references(client, operation, plan)
        current = api_tokens.eda_owned_token(client, item['receipt']['description'], item['expected'], allow_absent=True)
        require(current is not None and current['receipt'] == item['receipt']
                and current['token'] in (None, item['token_preimage']), 'The native EDA token changed after preflight.')
        outcome = api_tokens.eda_revoke_owned_token(client, item['receipt']['description'], item['expected'], item['receipt'], protected_ids)
        changed = changed or outcome['changed']
    access_tokens_absent(client, plan)
    return changed


def owner_preimage_matches(current, expected, selected, plan):
    """Allow validated cleanup additions, never attach an old plan to a new owner."""
    require(isinstance(current, dict) and isinstance(expected, dict),
            'Selected workload ownership disappeared or changed during cleanup.')
    now, before = deepcopy(current), deepcopy(expected)
    state, prior = now.pop('teardown', {}), before.pop('teardown', {})
    require(now == before and isinstance(state, dict) and isinstance(prior, dict)
            and set(state) <= {'subscription_absence', 'target_access_tokens'}
            and set(prior) <= set(state) and all(state[key] == value for key, value in prior.items()),
            'Selected workload ownership changed after native preflight; preserve it for review.')
    if 'target_access_tokens' in state:
        require(state['target_access_tokens'] == [item['receipt'] for item in plan.get('access_tokens', [])],
                'Retained token custody differs from this exact selected native plan.')
    if 'subscription_absence' in state:
        require(subscription_absence_valid(current, selected), 'Retained subscription proof is not valid for this exact selected TRA.')
    return True
