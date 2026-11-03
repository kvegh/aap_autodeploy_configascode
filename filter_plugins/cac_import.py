"""Bound one configuration import to reviewed data, resources and capabilities."""

from collections.abc import Mapping
from copy import deepcopy
import re
from urllib.parse import urlsplit

from ansible.errors import AnsibleFilterError


PROJECT_IDS = frozenset((
    "aiops-selfhealing-demo", "disconnected-windows-patching",
    "automation-orchestrator", "assistant-team", "aap_autodeploy_configascode",
))
RESOURCE_VARIABLES = frozenset((
    "aap_organizations", "aap_applications", "aap_teams", "aap_user_accounts",
    "controller_labels", "controller_credential_types", "controller_credentials",
    "controller_credential_input_sources", "controller_execution_environments",
    "controller_projects", "controller_inventories", "controller_inventory_sources",
    "controller_hosts", "controller_groups", "controller_templates", "controller_workflows",
    "controller_roles", "controller_schedules", "controller_launch_jobs",
    "controller_workflow_launch_jobs", "eda_credential_types", "eda_credentials",
    "eda_projects", "eda_event_streams", "eda_decision_environments",
    "eda_rulebook_activations",
))
FORBIDDEN_ROOTS = frozenset((
    "aap_hostname", "aap_target_hostname", "aap_username", "aap_password", "aap_token",
    "aap_validate_certs", "aap_instance_key", "aap_instance_route", "aap_cac_project_id",
    "aap_config_repo_url", "vault_cac_repository_namespace", "debug_logging",
    "dispatch_include_wildcard_vars", "aap_configuration_dispatcher_roles",
    "aap_configuration_dispatcher_exclude_roles", "aap_configuration_secure_logging",
    "cac_api_auth", "cac_project_contract", "cac_workspace", "cac_import_resources",
    "cac_gateway_token", "cac_service_preflight", "cac_configuration_ciphertexts", "cac_api_session_token",
    "hostvars", "groups", "inventory_hostname", "vars",
))
CAPABILITIES = {
    "eda_controller_access": {"credential_name", "organization", "token_variable"},
    "inventory_service_access": {"contract_variable", "password_variable"},
    "target_public_trust": {"ca_variable", "known_hosts_variable"},
}
PATH_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$")


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def variable_path(path):
    require(isinstance(path, str) and bool(PATH_PATTERN.fullmatch(path)),
            "Use a plain variable path in the configuration import metadata.")
    require(path.split('.')[0] not in FORBIDDEN_ROOTS
            and not path.startswith(('ansible_', 'cac_import_')),
            "Configuration metadata cannot reference importer or connection variables.")
    return path


def validate_capture_roots(data):
    require(isinstance(data, Mapping) and all(isinstance(key, str) for key in data)
            and not (set(data) & FORBIDDEN_ROOTS)
            and not any(key.startswith('ansible_') or key.endswith(('_dispatcher_roles', '_secure_logging'))
                        for key in data),
            'The capture must not override import authentication, execution or connection controls.')
    return True


def project_contract(project_id, namespace):
    require(isinstance(project_id, str) and project_id in PROJECT_IDS,
            "Select one of the five reviewed CaC project IDs.")
    require(isinstance(namespace, str) and not any(c.isspace() for c in namespace),
            "Configure the protected HTTPS CaC repository namespace.")
    try:
        parsed = urlsplit(namespace)
        port = parsed.port
    except ValueError:
        raise AnsibleFilterError("Invalid protected CaC repository namespace.") from None
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.path.count('/') == 1 and parsed.path not in ('', '/', '/.', '/..')
            and re.fullmatch(r'/[A-Za-z0-9_.-]+', parsed.path) and port in (None, 443),
            "Configure one HTTPS repository owner namespace without credentials or overrides.")
    return {'project_id': project_id, 'repository': namespace + '/' + project_id + '-secrets.git',
            'configuration_file': 'vaults/cac/' + project_id + '-cac-vault.yml'}


def import_metadata(metadata, project_id):
    require(project_id in PROJECT_IDS and isinstance(metadata, Mapping),
            "Load reviewed configuration import metadata for the selected project.")
    require(set(metadata) == {'schema_version', 'project_id', 'required_template_label',
                              'resource_variables', 'checks', 'capabilities'}
            and type(metadata.get('schema_version')) is int and metadata['schema_version'] == 1
            and metadata.get('project_id') == project_id,
            "The capture metadata does not match this project or supported schema.")
    require(isinstance(metadata['required_template_label'], str)
            and bool(metadata['required_template_label'])
            and '{{' not in metadata['required_template_label'],
            "Declare one literal project label for imported templates.")
    resources = metadata['resource_variables']
    require(isinstance(resources, Mapping) and resources
            and set(resources).issubset(RESOURCE_VARIABLES),
            "Map only explicitly supported configuration resource lists.")
    for path in resources.values():
        variable_path(path)
    checks = metadata['checks']
    require(isinstance(checks, Mapping)
            and set(checks).issubset({'true_values', 'empty_lists', 'required_secrets',
                                     'required_secret_lists', 'resource_counts'}),
            "Use only the supported configuration readiness checks.")
    for name in ('true_values', 'empty_lists', 'required_secrets', 'required_secret_lists'):
        require(isinstance(checks.get(name, []), list), "Readiness checks must be path lists.")
        for path in checks.get(name, []):
            variable_path(path)
    counts = checks.get('resource_counts', {})
    require(isinstance(counts, Mapping) and set(counts).issubset(resources)
            and all(type(count) is int and count >= 0 for count in counts.values()),
            "Declare exact counts only for resources imported by this capture.")
    capabilities = metadata['capabilities']
    require(isinstance(capabilities, Mapping) and set(capabilities).issubset(CAPABILITIES),
            "Unknown configuration preparation capability.")
    for name, config in capabilities.items():
        require(isinstance(config, Mapping) and set(config) == CAPABILITIES[name]
                and all(isinstance(value, str) and value for value in config.values()),
                "Incomplete configuration preparation capability.")
        for field, path in config.items():
            if field.endswith('_variable'):
                variable_path(path)
    return metadata


def read_path(variables, path):
    value = variables
    for component in variable_path(path).split('.'):
        require(isinstance(value, Mapping) and component in value,
                "A required configuration variable is missing.")
        value = value[component]
    return value


def resources_for_import(metadata, variables):
    import_metadata(metadata, metadata.get('project_id'))
    resources = {name: [] for name in RESOURCE_VARIABLES}
    for name, path in metadata['resource_variables'].items():
        value = read_path(variables, path)
        require(isinstance(value, list) and all(isinstance(row, Mapping) for row in value),
                "Every imported resource must be a list of configuration objects.")
        resources[name] = deepcopy(value)
    for name in ('controller_launch_jobs', 'controller_workflow_launch_jobs', 'controller_schedules'):
        require(not resources[name], "Configuration imports cannot launch jobs or install schedules.")
    for name, count in metadata['checks'].get('resource_counts', {}).items():
        require(len(resources[name]) == count, "A reviewed configuration resource count differs.")
    # Roles expect organization; the native Event Stream module also accepts the old alias.
    for stream in resources['eda_event_streams']:
        if 'organization_name' in stream:
            require('organization' not in stream or stream['organization'] == stream['organization_name'],
                    "Conflicting Event Stream organization aliases.")
            stream['organization'] = stream.pop('organization_name')
    return resources


def validate_checks(metadata, variables):
    checks = metadata['checks']
    for path in checks.get('true_values', []):
        require(read_path(variables, path) is True, "The configuration is not marked ready for import.")
    for path in checks.get('empty_lists', []):
        value = read_path(variables, path)
        require(isinstance(value, list) and not value, "Resolve the outstanding configuration review items.")
    secrets = list(checks.get('required_secrets', []))
    for path in checks.get('required_secret_lists', []):
        value = read_path(variables, path)
        require(isinstance(value, list), "Required secret names must be a list.")
        secrets.extend(value)
    for path in secrets:
        value = read_path(variables, path)
        require(isinstance(value, str) and value and value not in ('CHANGEME', '$encrypted$'),
                "Supply all required secrets through encrypted configuration.")
    return True


def api_target(selected_host, credential):
    """Bind native credential injection to the explicitly selected inventory host."""
    require(isinstance(selected_host, Mapping) and isinstance(credential, Mapping),
            "Select an inventory AAP instance and attach its native AAP API credential.")
    fqdn = selected_host.get('ansible_fqdn')
    require(isinstance(fqdn, str) and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', fqdn)
            and '.' in fqdn and '..' not in fqdn,
            "The selected inventory entry needs its full ansible_fqdn.")
    host = credential.get('hostname', '')
    try:
        parsed = urlsplit(host)
        port = parsed.port
    except ValueError:
        raise AnsibleFilterError("The destination credential needs a valid HTTPS origin.") from None
    require(parsed.scheme == 'https' and parsed.hostname == fqdn.lower()
            and port in (None, 443) and not parsed.username and not parsed.password
            and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
            and not any(c.isspace() for c in host),
            "The native API credential must identify the selected inventory FQDN over HTTPS.")
    require(credential.get('validate_certs') is True
            or str(credential.get('validate_certs')).lower() == 'true',
            "The destination AAP credential must enable TLS certificate verification.")
    token, username, password = (credential.get(name, '') for name in ('token', 'username', 'password'))
    require(all(isinstance(value, str) for value in (token, username, password))
            and ((bool(token) and not username and not password)
                 or (not token and bool(username) and bool(password))),
            "Attach an explicit destination bearer token OR username and password.")
    return {'hostname': host.rstrip('/'), 'token': token, 'username': username,
            'password': password, 'validate_certs': True}


def validate_resources(resources, metadata):
    for rows in resources.values():
        for row in rows:
            require(row.get('state', 'present') in ('present', 'enabled', 'disabled'),
                    'Configuration imports cannot delete resources.')
    if 'eda_controller_access' in metadata['capabilities']:
        streams, activations = resources['eda_event_streams'], resources['eda_rulebook_activations']
        require(bool(streams) and bool(activations), 'EDA Controller access requires reviewed streams and activations.')
        stream_names = set()
        for stream in streams:
            require(isinstance(stream.get('name'), str) and stream['name']
                    and stream.get('organization') == metadata['capabilities']['eda_controller_access']['organization']
                    and isinstance(stream.get('credential_name'), str) and stream['credential_name'],
                    'Each Event Stream requires its name, organization and credential.')
            stream_names.add(stream['name'])
        for activation in activations:
            mappings = activation.get('event_streams')
            require(isinstance(mappings, list) and bool(mappings), 'Every activation requires Event Stream mappings.')
            require(not activation.get('force_restart') and not activation.get('restart'),
                    'Configuration imports cannot restart activations.')
            for mapping in mappings:
                named = isinstance(mapping.get('source_name'), str) and bool(mapping['source_name'])
                indexed = type(mapping.get('source_index')) is int and mapping['source_index'] >= 0
                require(mapping.get('event_stream') in stream_names and named != indexed
                        and not ('source_name' in mapping and 'source_index' in mapping),
                        'Use a defined Event Stream with exactly one source name or index.')
    if 'inventory_service_access' in metadata['capabilities']:
        snapshots = [row for row in resources['controller_credentials']
                     if 'environment_vault' in row.get('inputs', {})]
        require(len(snapshots) == 1, 'Supply exactly one reviewed encrypted file snapshot credential.')
        for field in ('environment_vault', 'fresh_test_vault', 'retire_test_vault',
                      'claude_auth_recovery_vault', 'codex_auth_recovery_vault', 'bootstrap_auth_vault'):
            value = snapshots[0]['inputs'].get(field)
            require(isinstance(value, str) and re.match(r'^\$ANSIBLE_VAULT;1\.[12];AES256(;[^\r\n]+)?\r?\n', value),
                    'All embedded deployment/authentication snapshots must remain fully Vault encrypted.')
    return True


class FilterModule:
    def filters(self):
        return {'aap_cac_project_contract': project_contract,
                'aap_cac_import_metadata': import_metadata,
                'aap_cac_resources': resources_for_import,
                'aap_cac_read_path': read_path,
                'aap_cac_validate_checks': validate_checks,
                'aap_cac_api_target': api_target,
                'aap_cac_validate_resources': validate_resources}
