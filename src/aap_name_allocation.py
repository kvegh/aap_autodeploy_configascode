"""Reserve global test-VM names before provisioning; reservations never roll back."""

from copy import deepcopy
from ipaddress import IPv4Address
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import uuid

_spec = spec_from_file_location('allocation_interface_ownership', Path(__file__).with_name('aap_hypervisor_access.py'))
ownership = module_from_spec(_spec)
_spec.loader.exec_module(ownership)


def host_generation_request(state, prefix, hypervisor_id):
    """Find the single generation already consumed by this verified host install."""
    if (not isinstance(state, dict) or state.get('schema_version') != 1
            or not isinstance(state.get('reservations'), dict)):
        raise ValueError('Initialize the shared encrypted VM allocation state first.')
    matches = []
    for request_id, record in state['reservations'].items():
        if not isinstance(record, dict):
            raise ValueError('The shared allocation history is invalid.')
        installation = record.get('host_installation_id')
        if installation is None:
            continue
        if (not isinstance(installation, str) or not re.fullmatch(r'[a-f0-9]{64}', installation)
                or request_id != str(uuid.uuid5(uuid.NAMESPACE_URL, 'aap-host-install:' + installation))
                or not isinstance(record.get('number'), int) or isinstance(record['number'], bool)
                or not 1 <= record['number'] <= 99
                or record.get('vm_name') != '%s-%s' % (record.get('prefix'), record['number'])):
            raise ValueError('The shared host generation identity is invalid.')
        if record.get('hypervisor_id') == hypervisor_id:
            if record.get('decommissioned'):
                raise ValueError('A retired host generation cannot provision another guest.')
            if record.get('prefix') != prefix:
                raise ValueError('The host generation is bound to a different VM prefix.')
            matches.append(request_id)
    if len(matches) > 1:
        raise ValueError('The host identity has more than one shared generation.')
    return matches[0] if matches else None


def reserve(state, prefix, request_id, hypervisor_id, observed_floor=1):
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Initialize the shared encrypted VM allocation state first.")
    if not isinstance(prefix, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", prefix
    ):
        raise ValueError("Use a bounded lowercase VM-name prefix.")
    if not isinstance(request_id, str) or not re.fullmatch(
        r"[a-f0-9-]{36}", request_id
    ):
        raise ValueError("Use a unique reservation UUID.")
    if not isinstance(hypervisor_id, str) or not re.fullmatch(
        r"[a-f0-9]{32}", hypervisor_id
    ):
        raise ValueError(
            "Verify the selected hypervisor machine identity before reservation."
        )
    next_number = state.get("next_number")
    records = state.get("reservations")
    if (
        (not isinstance(next_number, int) or isinstance(next_number, bool))
        or next_number < 1
        or next_number >= 2**31
        or not isinstance(records, dict)
        or (not isinstance(observed_floor, int) or isinstance(observed_floor, bool))
        or observed_floor < 1
    ):
        raise ValueError("The shared allocation state is invalid.")
    numbers = [record["number"] for record in records.values()]
    names = [record["vm_name"] for record in records.values()]
    if (
        len(set(numbers)) != len(numbers)
        or len(set(names)) != len(names)
        or any((not isinstance(number, int) or isinstance(number, bool)) or number >= next_number for number in numbers)
    ):
        raise ValueError("Refuse inconsistent or regressed global allocation history.")
    if request_id in records:
        record = records[request_id]
        if record["hypervisor_id"] != hypervisor_id or record["prefix"] != prefix:
            raise ValueError("The reservation UUID is bound to a different request.")
        return deepcopy(state), deepcopy(record)
    if host_generation_request(state, prefix, hypervisor_id) is not None:
        raise ValueError('Reuse the verified host generation instead of consuming another number.')
    number = max(next_number, observed_floor)
    name = "%s-%s" % (prefix, number)
    if len(name) > 63:
        raise ValueError("The allocated hostname would be too long.")
    result = deepcopy(state)
    record = {
        "number": number,
        "vm_name": name,
        "prefix": prefix,
        "hypervisor_id": hypervisor_id,
    }
    result["reservations"][request_id] = record
    result["next_number"] = number + 1
    return result, deepcopy(record)


def reserve_host_generation(state, prefix, installation_id, hypervisor_id):
    """Consume the existing counter once, before publishing either host or VM name.

    The caller must first authenticate Rocky and prove the provider installation
    keys and machine identity. This pure allocator never establishes that trust.
    """
    if not isinstance(installation_id, str) or not re.fullmatch(r'[a-f0-9]{64}', installation_id):
        raise ValueError('Use the verified provider installation identity.')
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'aap-host-install:' + installation_id))
    updated, record = reserve(state, prefix, request_id, hypervisor_id)
    if record.get('decommissioned'):
        raise ValueError('A retired installation must not reserve another generation or provision a guest.')
    if record['number'] > 99:
        raise ValueError('Host deployment generations are exhausted at v99.')
    if record.get('host_installation_id') not in (None, installation_id):
        raise ValueError('The generation belongs to a different host installation.')
    # Never convert a pre-existing ordinary VM allocation into a host allocation.
    if request_id in state['reservations'] and record.get('host_installation_id') is None:
        raise ValueError('An existing ordinary VM reservation cannot become a host generation.')
    record['host_installation_id'] = installation_id
    updated['reservations'][request_id] = deepcopy(record)
    return updated, request_id, record


def validate_primary_resource(route, resource):
    """Bind the existing primary ownership record to this exact verified route."""
    if (not isinstance(resource, dict) or not ownership.PRIMARY_FIELDS <= set(resource)
            or set(resource) - ownership.PRIMARY_FIELDS - {'supplemental_interfaces'}):
        raise ValueError("Publish only the complete verified primary guest ownership fields.")
    if (not isinstance(resource["uuid"], str)
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", resource["uuid"])
            or resource["uuid"] == "00000000-0000-0000-0000-000000000000"
            or resource["disk"] != "/opt/vms/" + route["vm_name"] + ".disk.qcow2"
            or resource["address"] != route["vm_ip"]
            or not isinstance(resource["address"], str)
            or str(IPv4Address(resource["address"])) != resource["address"]
            or not isinstance(resource["mac"], str)
            or not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", resource["mac"])
            or int(resource["mac"][:2], 16) & 1 or resource["mac"] == "00:00:00:00:00:00"
            or not isinstance(resource["network"], str)
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", resource["network"])
            or resource["bridge"] not in route["hypervisor"]["isolation_bridges"]
            or resource["hypervisor_machine_id"] != route["hypervisor"]["machine_id"]
            or resource["verified"] is not True):
        raise ValueError("Primary guest ownership must match the exact selected route, disk and pinned hypervisor.")
    ownership.primary_interfaces(resource, route['hypervisor'])
    return resource


def publish_route(state, request_id, route, instance_resources=None):
    if request_id not in state["reservations"]:
        raise ValueError(
            "Reserve the name before publishing its verified instance route."
        )
    record = state["reservations"][request_id]
    if record.get("decommissioned"):
        raise ValueError("A decommissioned reservation cannot publish an active guest route.")
    if (
        route["vm_name"] != record["vm_name"]
        or route["hypervisor"]["machine_id"] != record["hypervisor_id"]
    ):
        raise ValueError("The instance route does not match its consumed reservation.")
    if record.get("instance_route") not in (None, route):
        raise ValueError(
            "An existing verified instance route cannot be silently replaced."
        )
    updated = deepcopy(state)
    updated["reservations"][request_id]["instance_route"] = deepcopy(route)
    if instance_resources is not None:
        if not isinstance(instance_resources, dict) or set(instance_resources) != {"aap"}:
            raise ValueError("Route publication may update only its verified primary AAP resource.")
        resource = validate_primary_resource(route, instance_resources["aap"])
        existing = record.get("instance_resources", {})
        if not isinstance(existing, dict) or set(existing) - {"aap"} or existing.get("aap") not in (None, resource):
            raise ValueError("Existing primary guest ownership cannot be silently replaced.")
        updated["reservations"][request_id].setdefault("instance_resources", {})["aap"] = deepcopy(resource)
    return updated, deepcopy(updated["reservations"][request_id])


def main(argv=None):
    """Existing host-counter adapter: private local Vault transaction, no Git/API."""
    import argparse
    import fcntl
    import hashlib
    import json
    import os
    import stat
    import sys
    import tempfile
    import yaml
    from ansible.parsing.vault import VaultLib, VaultSecret
    from cac_yaml import VaultDumper, literal_paths, load_repository_yaml

    parser = argparse.ArgumentParser(description='Reserve one shared host/AAP generation from an existing encrypted registry.')
    parser.add_argument('operation', choices=['reserve-host'])
    parser.add_argument('--registry', required=True)
    parser.add_argument('--vault-password-file', required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--installation-id', required=True)
    parser.add_argument('--hypervisor-id', required=True)
    # Avoid argparse echoing rejected private argument values.
    parser.error = lambda message: parser.exit(2, 'Invalid shared allocation arguments; use --help.\n')
    args = parser.parse_args(argv)
    temporary = None
    try:
        password_path = Path(args.vault_password_file)
        with os.fdopen(os.open(password_path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) not in (0o400, 0o600):
                raise ValueError('Use a protected regular Vault password file.')
            secret = VaultSecret(stream.read().strip())
        vault = VaultLib([('default', secret)])
        path = Path(args.registry)
        with os.fdopen(os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'r+b') as lock:
            if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
                raise ValueError('Use a regular allocation lock file.')
            fcntl.flock(lock, fcntl.LOCK_EX)

            def read_ciphertext():
                with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError('Use an existing regular encrypted allocation file.')
                    return stream.read()

            original = read_ciphertext()
            header = original.splitlines()[0]
            if header != b'$ANSIBLE_VAULT;1.1;AES256' and not re.fullmatch(rb'\$ANSIBLE_VAULT;1.2;AES256;[A-Za-z0-9_-]+', header):
                raise ValueError('Use the existing supported encrypted allocation file.')
            configuration = load_repository_yaml(vault.decrypt(original))
            state = configuration['aap_vm_allocation']
            updated, request_id, record = reserve_host_generation(
                state, args.prefix, args.installation_id, args.hypervisor_id)
            changed = updated != state
            if changed:
                configuration['aap_vm_allocation'] = updated
                encoded = yaml.dump(configuration, Dumper=VaultDumper, sort_keys=False, width=110).encode()
                label = header.decode().split(';')[3] if header.count(b';') == 3 else None
                sealed = vault.encrypt(encoded, secret=secret, vault_id=label)
                readback = load_repository_yaml(vault.decrypt(sealed))
                if (sealed.splitlines()[0] != header or readback != configuration
                        or literal_paths(readback) != literal_paths(configuration)):
                    raise ValueError('Shared allocation Vault roundtrip failed.')
                with tempfile.NamedTemporaryFile(prefix=path.name + '.', dir=path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    os.fchmod(stream.fileno(), 0o600)
                    stream.write(sealed.rstrip(b'\n') + b'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                if hashlib.sha256(read_ciphertext()).digest() != hashlib.sha256(original).digest():
                    raise ValueError('The allocation file changed during this transaction.')
                os.replace(temporary, path)
                temporary = None
                descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            result = dict(number=record['number'], request_id=request_id, changed=changed, reused=not changed)
    except Exception:
        # Ansible/Vault/YAML errors can include secret or environmental values.
        print('Shared generation reservation failed; no allocation was confirmed.', file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
