"""Preserve explicit literal-template tags when writing protected CaC YAML."""

from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.utils.unsafe_proxy import AnsibleUnsafeText, NativeJinjaUnsafeText


class VaultDumper(AnsibleDumper):
    """AnsibleDumper otherwise serializes unsafe strings as ordinary text."""


def literal_text(dumper, value):
    return dumper.represent_scalar("!unsafe", value._strip_unsafe())


VaultDumper.add_representer(AnsibleUnsafeText, literal_text)
VaultDumper.add_representer(NativeJinjaUnsafeText, literal_text)
VaultDumper.add_multi_representer(AnsibleUnsafeText, literal_text)


def literal_paths(value, path=()):
    if isinstance(value, dict):
        return set().union(
            *(literal_paths(item, path + (key,)) for key, item in value.items())
        )
    if isinstance(value, list):
        return set().union(
            *(literal_paths(item, path + (index,)) for index, item in enumerate(value))
        )
    return {path} if isinstance(value, AnsibleUnsafeText) else set()
