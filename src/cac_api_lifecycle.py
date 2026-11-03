"""Target API lifecycle operations, run only in the source execution environment."""

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener
import ssl


class LifecycleError(Exception):
    """A collision or incomplete state requiring explicit recovery."""


def require(condition, message):
    if not condition:
        raise LifecycleError(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class Client:
    def __init__(self, hostname, token, username='', password=''):
        self.hostname, self.token = hostname, token
        self.basic = (username, password) if not token else None
        self.opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())

    def request(self, method, path, body=None, basic=None, token=None):
        require(path.startswith('/api/') and '://' not in path, 'Unexpected lifecycle API path.')
        auth = 'Bearer ' + (self.token if token is None else token)
        if basic is None and token is None:
            basic = self.basic
        if basic is not None:
            auth = 'Basic ' + base64.b64encode((':'.join(basic)).encode()).decode()
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.hostname + path, data=data, method=method,
                          headers={'Authorization': auth, 'Accept': 'application/json',
                                   'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=45) as response:
                content = response.read()
                return json.loads(content) if content else {}
        except HTTPError as error:
            raise LifecycleError('The target rejected a lifecycle API request (HTTP %s).' % error.code) from None
        except (URLError, ssl.SSLError, ValueError):
            raise LifecycleError('Verified target API connection failed; no alternate connection was attempted.') from None

    def rows(self, path):
        result = self.request('GET', path)
        require(isinstance(result, dict) and result.get('next') is None
                and isinstance(result.get('results'), list)
                and result.get('count') == len(result['results']),
                'Lifecycle API results are incomplete or ambiguous.')
        return result['results']


def query(**kwargs):
    return '?' + urlencode(kwargs)


def one(rows, label):
    require(len(rows) == 1, 'Require exactly one ' + label + '; existing resources were preserved.')
    return rows[0]


def unprivileged(user):
    return (user.get('is_superuser') is False
            and user.get('is_platform_auditor', False) is False
            and user.get('is_system_auditor', False) is False)


def service_preflight(client, contract, password, resources):
    """Check collisions before dispatch; omit passwords for authenticated existing users."""
    required = {'username', 'inventory', 'organization', 'credential_name',
                'credential_type_name', 'token_description'}
    require(isinstance(contract, dict) and required.issubset(contract)
            and all(isinstance(contract[key], str) and contract[key] for key in required)
            and isinstance(password, str) and len(password) >= 48,
            'Supply a reviewed dedicated service contract and encrypted long password.')
    users, roles = resources['aap_user_accounts'], resources['controller_roles']
    require(len(users) == 1 and users[0].get('username') == contract['username']
            and users[0].get('password') == password and unprivileged(users[0])
            and users[0].get('update_secrets') is False
            and len(roles) == 1 and roles[0].get('user') == contract['username']
            and roles[0].get('inventory') == contract['inventory'] and roles[0].get('role') == 'admin',
            'The service definition must contain one nonprivileged user and one inventory-only grant.')
    types = [row for row in resources['controller_credential_types']
             if row.get('name') == contract['credential_type_name']]
    expected_type = one(types, 'reviewed service credential type')
    found_types = client.rows('/api/controller/v2/credential_types/' + query(name=contract['credential_type_name']))
    require(len(found_types) <= 1, 'Duplicate service credential types require review.')
    if found_types:
        require(all(found_types[0].get(key) == expected_type.get(key)
                    for key in ('kind', 'inputs', 'injectors')), 'The existing service credential schema differs.')
    inventories = client.rows('/api/controller/v2/inventories/' + query(name=contract['inventory']))
    require(len(inventories) <= 1 and (not inventories or inventories[0].get('summary_fields', {})
            .get('organization', {}).get('name') == contract['organization']),
            'The dedicated service inventory is ambiguous or belongs to another organization.')
    found = client.rows('/api/gateway/v1/users/' + query(username=contract['username']))
    require(len(found) <= 1 and all(unprivileged(user) for user in found),
            'A privileged or ambiguous service account must not be reused.')
    result = deepcopy(resources)
    if found:
        controller_user = one(client.rows('/api/controller/v2/users/' + query(username=contract['username'])),
                              'matching Controller service user')
        require(unprivileged(controller_user), 'The Controller service user must not be privileged.')
        validate_grants(client, controller_user, inventories[0]['id'] if inventories else None, allow_empty=True)
        identity = client.request('GET', '/api/gateway/v1/me/', basic=(contract['username'], password))
        principals = identity.get('results', [identity])
        principal = one(principals, 'authenticated service identity')
        require(principal.get('id') == found[0]['id'] and unprivileged(principal),
                'The prepared service password does not identify the expected nonprivileged user.')
        result['aap_user_accounts'][0].pop('password', None)
    return result, expected_type


def validate_grants(client, user, inventory_id, allow_empty=False):
    grants = client.rows('/api/controller/v2/role_user_assignments/' + query(user=user['id']))
    teams = client.rows('/api/controller/v2/users/%s/teams/' % user['id'])
    require(not teams and ((allow_empty and not grants) or (len(grants) == 1
            and grants[0].get('content_type') == 'awx.inventory'
            and str(grants[0].get('object_id')) == str(inventory_id)
            and grants[0].get('summary_fields', {}).get('role_definition', {}).get('name') == 'Inventory Admin')),
            'Unexpected service grants or team membership require review; no permissions were removed.')


def valid_token(token, user, description):
    require(token.get('user') == user and token.get('description') == description
            and token.get('scope') == 'write' and token.get('application') is None
            and type(token.get('id')) is int, 'Unexpected service token identity, scope or application.')
    if token.get('expires'):
        try:
            expires = datetime.fromisoformat(token['expires'].replace('Z', '+00:00'))
            require(expires > datetime.now(timezone.utc), 'The existing service token has expired; recovery is explicit.')
        except (TypeError, ValueError):
            raise LifecycleError('The service token expiry requires review.') from None


def service_access(client, contract, password, credential_type, ca):
    """Persist service access in its target credential; never scrape or copy a seed token."""
    organization = one(client.rows('/api/controller/v2/organizations/' + query(name=contract['organization'])), 'organization')
    inventory = one(client.rows('/api/controller/v2/inventories/' + query(name=contract['inventory'])), 'dedicated inventory')
    require(inventory.get('organization') == organization['id'], 'The service inventory organization differs.')
    gateway_user = one(client.rows('/api/gateway/v1/users/' + query(username=contract['username'])), 'Gateway service user')
    controller_user = one(client.rows('/api/controller/v2/users/' + query(username=contract['username'])), 'Controller service user')
    require(unprivileged(gateway_user) and unprivileged(controller_user), 'Service access requires a nonprivileged user.')
    validate_grants(client, controller_user, inventory['id'])
    stored_type = one(client.rows('/api/controller/v2/credential_types/' + query(name=credential_type['name'])), 'service type')
    require(all(stored_type.get(key) == credential_type.get(key) for key in ('kind', 'inputs', 'injectors')),
            'The service credential type changed after validation.')
    credentials = client.rows('/api/controller/v2/credentials/' + query(name=contract['credential_name']))
    tokens = client.rows('/api/gateway/v1/tokens/' + query(description=contract['token_description'], user=gateway_user['id']))
    require(len(credentials) <= 1 and len(tokens) <= 1, 'Duplicate service credentials/tokens require explicit review.')
    for token in tokens:
        valid_token(token, gateway_user['id'], contract['token_description'])
    public = {'controller_host': client.hostname, 'controller_ca': ca, 'inventory_id': str(inventory['id'])}
    binding = {'target': client.hostname, 'user': gateway_user['id'], 'controller_user': controller_user['id'],
               'inventory': inventory['id'], 'organization': organization['id'], 'credential_type': stored_type['id'],
               'ca_sha256': hashlib.sha256(ca.encode()).hexdigest()}
    if credentials:
        require(len(tokens) == 1, 'The existing service credential has no unique service token; preserve it for explicit recovery.')
        old = credentials[0]
        expected_description = binding_description(contract, binding, tokens[0]['id'])
        inputs = old.get('inputs', {})
        require(old.get('organization') == organization['id'] and old.get('credential_type') == stored_type['id']
                and old.get('description') == expected_description
                and all(inputs.get(key) == value for key, value in public.items())
                and inputs.get('controller_token') and inputs.get('material_sha256'),
                'The masked service credential cannot be verified against its API-only binding; explicit recovery is required.')
        # Do not send masked write-only inputs back or mint another bearer on a rerun.
        return {'changed': False, 'credential_id': old['id']}
    require(not tokens, 'A service token already exists without its credential; explicit recovery is required.')
    created = None
    try:
        created = client.request('POST', '/api/gateway/v1/tokens/',
                                 {'description': contract['token_description'], 'scope': 'write', 'application': None},
                                 basic=(contract['username'], password))
        valid_token(created, gateway_user['id'], contract['token_description'])
        require(isinstance(created.get('token'), str) and created['token'], 'The new service bearer was not returned.')
        principal = one(client.request('GET', '/api/controller/v2/me/', token=created['token']).get('results', []),
                        'authenticated service user')
        require(principal.get('id') == controller_user['id'] and unprivileged(principal), 'The new service token identifies another user.')
        material = dict(public, controller_token=created['token'])
        material['material_sha256'] = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        credential = client.request('POST', '/api/controller/v2/credentials/',
                                    {'name': contract['credential_name'], 'organization': organization['id'],
                                     'credential_type': stored_type['id'], 'inputs': material,
                                     'description': binding_description(contract, binding, created['id'])})
        require(type(credential.get('id')) is int, 'The target did not confirm stored service access.')
        return {'changed': True, 'credential_id': credential['id']}
    except Exception:
        if created is not None and type(created.get('id')) is int:
            # Unknown persistence outcomes preserve the bearer. Revoke only proved-unsaved creation.
            try:
                missing = not client.rows('/api/controller/v2/credentials/' + query(name=contract['credential_name']))
            except Exception:
                missing = False
            if missing:
                client.request('DELETE', '/api/gateway/v1/tokens/%s/' % created['id'])
        raise


def binding_description(contract, binding, token_id):
    digest = hashlib.sha256(json.dumps(dict(binding, token_id=token_id), sort_keys=True).encode()).hexdigest()
    return contract['token_description'] + ' [CaC API binding ' + digest + ']'


def eda_access(client, capability, definitions):
    definition = one([row for row in definitions if row.get('name') == capability['credential_name']],
                     'persistent EDA Controller credential definition')
    expected = deepcopy(definition)
    require(expected.get('organization') == capability['organization']
            and expected.get('credential_type') == 'Red Hat Ansible Automation Platform'
            and expected.get('inputs', {}).get('host', '').rstrip('/') == client.hostname + '/api/controller',
            'The EDA Controller credential must be bound to this target and organization.')
    endpoint = '/api/eda/v1/eda-credentials/' + query(name=expected['name'])
    found = client.rows(endpoint)
    require(len(found) <= 1, 'Duplicate EDA Controller credentials require review.')
    if found:
        old = found[0]
        require(old.get('organization', {}).get('name') == capability['organization']
                and old.get('credential_type', {}).get('name') == expected['credential_type']
                and old.get('inputs', {}).get('oauth_token')
                and old['inputs'].get('host', '').rstrip('/') == client.hostname + '/api/controller'
                and {key: value for key, value in old['inputs'].items() if key not in ('oauth_token', 'host')}
                == {key: value for key, value in expected['inputs'].items() if key not in ('oauth_token', 'host')}
                and ('description' not in expected or old.get('description') == expected['description']),
                'The stored EDA credential differs; its write-only token was preserved.')
        return {'changed': False}
    organization = one(client.rows('/api/eda/v1/organizations/' + query(name=capability['organization'])), 'EDA organization')
    credential_type = one(client.rows('/api/eda/v1/credential-types/' + query(name=expected['credential_type'])), 'EDA credential type')
    created = None
    try:
        created = client.request('POST', '/api/gateway/v1/tokens/',
                                 {'description': 'CaC EDA Controller access: ' + expected['name'],
                                  'scope': 'write', 'application': None})
        require(type(created.get('id')) is int and isinstance(created.get('token'), str) and created['token'],
                'The target did not return a persistent EDA token.')
        inputs = dict(expected['inputs'], oauth_token=created['token'])
        client.request('POST', '/api/eda/v1/eda-credentials/',
                       {'name': expected['name'], 'description': expected.get('description', ''),
                        'organization_id': organization['id'], 'credential_type_id': credential_type['id'], 'inputs': inputs})
        require(len(client.rows(endpoint)) == 1, 'The target did not confirm saved EDA access.')
        return {'changed': True}
    except Exception:
        if created is not None and type(created.get('id')) is int:
            try:
                missing = not client.rows(endpoint)
            except Exception:
                missing = False
            if missing:
                client.request('DELETE', '/api/gateway/v1/tokens/%s/' % created['id'])
        raise
