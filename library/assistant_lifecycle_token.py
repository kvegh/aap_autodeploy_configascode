#!/usr/bin/python
"""Keep an inventory service token on its own target; never copy seed tokens."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import stat
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

DOCUMENTATION = r'''
---
module: assistant_lifecycle_token
short_description: Preserve target-local inventory service access
description:
  - Requires an existing inventory-scoped user, grant and compatible credential type.
  - Issues a service-user token only when neither its API metadata nor private copy exists.
  - Verifies TLS, identity, permissions and existing credential bindings before reuse.
options:
  hostname:
    type: str
    required: true
  admin_token:
    type: str
    required: true
    no_log: true
  username:
    type: str
    required: true
  password:
    type: str
    required: true
    no_log: true
  inventory:
    type: str
    required: true
  organization:
    type: str
    required: true
  credential:
    type: str
    required: true
  credential_type:
    type: dict
    required: true
  description:
    type: str
    required: true
  ca_path:
    type: path
    required: true
  storage_path:
    type: path
    default: /var/lib/aap-autodeploy/assistant-team-inventory-token.json
author: AAP AutoDeploy maintainers
'''


class LifecycleError(Exception):
    """A recoverable mismatch that must not trigger automatic rotation."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class Client:
    def __init__(self, hostname, admin_token, ca_path):
        parsed = urlsplit(hostname)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise LifecycleError('Supply an HTTPS target origin without credentials or a path.')
        self.hostname = hostname.rstrip('/')
        self.admin_token = admin_token
        # This verifies both the CA chain and the URL's hostname/IP SAN.
        self.context = ssl.create_default_context(cafile=ca_path)
        self.opener = build_opener(HTTPSHandler(context=self.context), NoRedirect())

    def request(self, method, path, body=None, token=None, basic=None):
        if not path.startswith('/api/') or '://' in path:
            raise LifecycleError('Unexpected API path.')
        authorization = 'Bearer ' + (token if token is not None else self.admin_token)
        if basic is not None:
            authorization = 'Basic ' + base64.b64encode((basic[0] + ':' + basic[1]).encode()).decode()
        headers = {'Authorization': authorization, 'Accept': 'application/json', 'Content-Type': 'application/json'}
        data = json.dumps(body).encode() if body is not None else None
        try:
            with self.opener.open(Request(self.hostname + path, data=data, headers=headers, method=method),
                                  timeout=45) as response:
                payload = response.read()
                return json.loads(payload) if payload else {}
        except HTTPError as error:
            raise LifecycleError('Target API rejected lifecycle request (HTTP %s).' % error.code) from None
        except (URLError, ssl.SSLError, ValueError):
            raise LifecycleError('Verified target HTTPS request failed; check CA, hostname and connectivity.') from None

    def rows(self, path):
        result = self.request('GET', path)
        if (not isinstance(result, dict) or result.get('next') is not None
                or not isinstance(result.get('results'), list)
                or result.get('count') != len(result['results'])):
            raise LifecycleError('Incomplete or ambiguous API result; review before retrying.')
        return result['results']


class Store:
    def __init__(self, filename, owner=0):
        self.path = Path(filename)
        self.owner = owner

    def check_directory(self):
        info = self.path.parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != self.owner or stat.S_IMODE(info.st_mode) != 0o700:
            raise LifecycleError('Require a private owned token directory with mode 0700.')

    def read(self):
        self.check_directory()
        try:
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError:
            raise LifecycleError('Cannot safely inspect the token file; preserve existing access.') from None
        with os.fdopen(descriptor) as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.owner
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise LifecycleError('Require an owned regular token file with mode 0600.')
            try:
                document = json.load(stream)
            except (ValueError, OSError):
                raise LifecycleError('The token file needs explicit recovery; it was not replaced.') from None
        return document

    def write(self, document):
        self.check_directory()
        descriptor, name = tempfile.mkstemp(prefix='.assistant-token-', dir=str(self.path.parent))
        try:
            with os.fdopen(descriptor, 'w') as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump(document, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def unique(rows, label):
    if len(rows) != 1:
        raise LifecycleError('Require exactly one ' + label + '; existing resources were preserved.')
    return rows[0]


def token_valid(token, user, description):
    if (token.get('user') != user or token.get('scope') != 'write'
            or token.get('application') is not None or token.get('description') != description
            or not isinstance(token.get('id'), int)):
        raise LifecycleError('Unexpected lifecycle token owner, scope, application or description.')
    if token.get('expires'):
        try:
            expires = datetime.fromisoformat(token['expires'].replace('Z', '+00:00'))
            if expires <= datetime.now(timezone.utc):
                raise ValueError()
        except (TypeError, ValueError):
            raise LifecycleError('Lifecycle token expiry needs explicit review; access was preserved.') from None


def reconcile(client, config, store, check_mode=False):
    query = lambda **kwargs: '?' + urlencode(kwargs)
    organization = unique(client.rows('/api/controller/v2/organizations/' + query(name=config['organization'])), 'organization')
    inventory = unique(client.rows('/api/controller/v2/inventories/' + query(name=config['inventory'])), 'dedicated inventory')
    if inventory['organization'] != organization['id']:
        raise LifecycleError('The lifecycle inventory belongs to an unexpected organization.')
    gateway_user = unique(client.rows('/api/gateway/v1/users/' + query(username=config['username'])), 'Gateway service user')
    controller_user = unique(client.rows('/api/controller/v2/users/' + query(username=config['username'])), 'Controller service user')
    if (gateway_user.get('is_superuser') is not False or gateway_user.get('is_platform_auditor') is not False
            or controller_user.get('is_superuser') is not False or controller_user.get('is_system_auditor') is not False):
        raise LifecycleError('Lifecycle access requires a nonadministrator, nonauditor service user.')
    assignments = client.rows('/api/controller/v2/role_user_assignments/' + query(user=controller_user['id']))
    if (len(assignments) != 1 or assignments[0].get('content_type') != 'awx.inventory'
            or str(assignments[0].get('object_id')) != str(inventory['id'])
            or assignments[0].get('summary_fields', {}).get('role_definition', {}).get('name') != 'Inventory Admin'):
        raise LifecycleError('Service user must have exactly the dedicated inventory administrator grant.')
    if client.rows('/api/controller/v2/users/%s/teams/' % controller_user['id']):
        raise LifecycleError('Lifecycle service identity has unexpected team membership.')
    credential_type = unique(client.rows('/api/controller/v2/credential_types/' + query(name=config['credential_type']['name'])), 'lifecycle credential type')
    for field in ('kind', 'inputs', 'injectors'):
        if credential_type.get(field) != config['credential_type'].get(field):
            raise LifecycleError('Existing lifecycle credential type has a different purpose/schema.')
    existing_credentials = client.rows('/api/controller/v2/credentials/' + query(name=config['credential']))
    if len(existing_credentials) > 1:
        raise LifecycleError('Duplicate lifecycle credentials need explicit review.')

    ca = Path(config['ca_path']).read_text()
    expected = {'target': client.hostname, 'username': config['username'], 'user_id': gateway_user['id'],
                'controller_user_id': controller_user['id'], 'inventory_id': inventory['id'],
                'ca_sha256': hashlib.sha256(ca.encode()).hexdigest(), 'scope': 'write'}
    tokens = client.rows('/api/gateway/v1/tokens/' + query(description=config['description'], user=gateway_user['id']))
    if len(tokens) > 1:
        raise LifecycleError('Duplicate lifecycle tokens need explicit review; none were revoked.')
    for token in tokens:
        token_valid(token, gateway_user['id'], config['description'])
    record = store.read()
    if record is not None:
        if (not isinstance(record, dict) or any(record.get(key) != value for key, value in expected.items())
                or len(tokens) != 1 or record.get('token_id') != tokens[0]['id']
                or not isinstance(record.get('token'), str) or not record['token']):
            raise LifecycleError('Saved lifecycle binding differs; review without rotating existing access.')
    elif tokens or existing_credentials:
        raise LifecycleError('Existing lifecycle access has no recoverable target-local token copy.')
    if record is None and check_mode:
        return {'changed': True, 'requires_token_creation': True}

    created = None
    try:
        if record is None:
            created = client.request('POST', '/api/gateway/v1/tokens/',
                                     {'description': config['description'], 'scope': 'write', 'application': None},
                                     basic=(config['username'], config['password']))
            token_valid(created, gateway_user['id'], config['description'])
            if not isinstance(created.get('token'), str) or not created['token']:
                raise LifecycleError('Gateway did not return the new service token.')
            record = dict(expected, token_id=created['id'], token=created['token'], expires=created.get('expires'))
        identity = client.request('GET', '/api/controller/v2/me/', token=record['token'])
        principal = unique(identity.get('results', []), 'authenticated lifecycle identity')
        if (principal.get('id') != controller_user['id'] or principal.get('username') != config['username']
                or principal.get('is_superuser') is not False or principal.get('is_system_auditor') is not False):
            raise LifecycleError('Saved lifecycle bearer identifies an unexpected principal.')
        material = {'controller_token': record['token'], 'controller_ca': ca,
                    'controller_host': client.hostname, 'inventory_id': str(inventory['id'])}
        checksum = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        if existing_credentials:
            old = existing_credentials[0]
            inputs = old.get('inputs', {})
            if (old.get('organization') != organization['id'] or old.get('credential_type') != credential_type['id']
                    or any(inputs.get(key) != material[key] for key in ('controller_host', 'inventory_id', 'controller_ca'))
                    or inputs.get('material_sha256') != checksum or not inputs.get('controller_token')):
                raise LifecycleError('Existing lifecycle credential type, organization or bound material differs.')
        if created is not None:
            after = client.rows('/api/gateway/v1/tokens/' + query(description=config['description'], user=gateway_user['id']))
            if len(after) != 1 or after[0]['id'] != created['id']:
                raise LifecycleError('Concurrent lifecycle token creation needs explicit review.')
            store.write(record)
        material['material_sha256'] = checksum
        return {'changed': created is not None, 'credential_inputs': material,
                'inventory_id': inventory['id'], 'user_id': controller_user['id'], 'token_id': record['token_id']}
    except Exception:
        if created is not None and isinstance(created.get('id'), int):
            # An interrupted save may already have replaced the file. Preserve
            # that bearer. Revoke only this run's proved-unsaved new token.
            try:
                saved = store.read()
                proved_unsaved = saved is None or saved.get('token') != created.get('token')
            except Exception:
                proved_unsaved = False
            if proved_unsaved:
                client.request('DELETE', '/api/gateway/v1/tokens/%s/' % created['id'])
        raise


def main():
    from ansible.module_utils.basic import AnsibleModule
    module = AnsibleModule(argument_spec={
        'hostname': {'type': 'str', 'required': True}, 'admin_token': {'type': 'str', 'required': True, 'no_log': True},
        'username': {'type': 'str', 'required': True}, 'password': {'type': 'str', 'required': True, 'no_log': True},
        'inventory': {'type': 'str', 'required': True}, 'organization': {'type': 'str', 'required': True},
        'credential': {'type': 'str', 'required': True}, 'credential_type': {'type': 'dict', 'required': True},
        'description': {'type': 'str', 'required': True}, 'ca_path': {'type': 'path', 'required': True},
        'storage_path': {'type': 'path', 'default': '/var/lib/aap-autodeploy/assistant-team-inventory-token.json'},
    }, supports_check_mode=True)
    try:
        if os.geteuid() != 0:
            raise LifecycleError('Run on the target AAP with root-owned protected storage.')
        client = Client(module.params['hostname'], module.params['admin_token'], module.params['ca_path'])
        result = reconcile(client, module.params, Store(module.params['storage_path']), module.check_mode)
    except LifecycleError as error:
        module.fail_json(msg=str(error))
    except Exception:
        module.fail_json(msg='Lifecycle provisioning failed; inspect target state before retrying. Existing access was preserved unless a new unsaved token was proved absent from storage.')
    module.exit_json(**result)


if __name__ == '__main__':
    main()
