"""Preserve explicit literal-template tags when writing protected CaC YAML."""

from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.template import is_trusted_as_template, trust_as_template


def literal_template(value):
    """Core 2.20 represents literal templates through trust tags, not subclasses."""
    return (isinstance(value, str)
            and any(marker in value for marker in ("{{", "{%", "{#"))
            and not is_trusted_as_template(value))


def VaultDumper(*args, **kwargs):
    """Keep literal templates explicit without modifying Ansible's global dumper."""
    # AnsibleDumper is a factory in core 2.20. Its default serializer discards
    # trust tags, so preserve literal templates before that conversion occurs.
    dumper = AnsibleDumper(*args, **kwargs)
    original = dumper.represent_data

    def represent_data(value):
        if isinstance(value, str) and any(marker in value for marker in ("{{", "{%", "{#")):
            # Handle trusted strings too: the vendor's tag-stripping recursion
            # would otherwise revisit them as ordinary, untrusted strings.
            tag = "!unsafe" if literal_template(value) else "tag:yaml.org,2002:str"
            return dumper.represent_scalar(tag, str(value))
        return original(value)

    dumper.represent_data = represent_data
    return dumper


def load_repository_yaml(plaintext):
    """Load reviewed repository configuration; never use this for API responses.

    Trust the configuration source as Ansible does for repository vars files.
    The native !unsafe constructor still removes trust from literal values.
    """
    if isinstance(plaintext, bytes):
        plaintext = plaintext.decode("utf-8")
    return AnsibleLoader(trust_as_template(plaintext)).get_single_data()


def literal_paths(value, path=()):
    if isinstance(value, dict):
        return set().union(
            *(literal_paths(item, path + (key,)) for key, item in value.items())
        )
    if isinstance(value, list):
        return set().union(
            *(literal_paths(item, path + (index,)) for index, item in enumerate(value))
        )
    return {path} if literal_template(value) else set()
