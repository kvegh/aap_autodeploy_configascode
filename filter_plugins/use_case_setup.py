"""Bound selected configuration imports to reviewed umbrella submodules."""
from collections.abc import Mapping
from urllib.parse import urlsplit

from ansible.errors import AnsibleFilterError


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def https_origin(value):
    require(isinstance(value, str) and not any(c.isspace() for c in value),
            'Supply an explicit HTTPS AAP origin.')
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise AnsibleFilterError('The AAP URL is invalid.') from None
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and parsed.path in ('', '/')
            and not parsed.query and not parsed.fragment,
            'AAP URLs must be HTTPS origins without credentials or extra paths.')
    return parsed.hostname.lower(), port or 443


def git_url(value):
    require(isinstance(value, str) and not any(c.isspace() for c in value),
            'Supply an explicit HTTPS Git URL.')
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise AnsibleFilterError('The Git URL is invalid.') from None
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and parsed.path not in ('', '/')
            and not parsed.query and not parsed.fragment,
            'Use HTTPS Git URLs without embedded credentials, query or fragment.')
    return value.rstrip('/').removesuffix('.git')


def setup_plan(selected, catalog, protected, seed, target):
    require(https_origin(seed) != https_origin(target),
            'The fresh target must differ from the seed AAP.')
    require(isinstance(selected, list) and selected
            and all(isinstance(key, str) for key in selected)
            and len(set(selected)) == len(selected),
            'Choose a nonempty unique list of use-case submodules.')
    require(isinstance(catalog, Mapping) and isinstance(protected, Mapping),
            'Load the reviewed use-case catalog from encrypted configuration.')
    modules = protected.get('umbrella_modules', {})
    repositories = protected.get('configuration_repositories', {})
    require(isinstance(modules, Mapping) and set(modules) == set(catalog),
            'Refresh the reviewed umbrella submodule catalog before setup.')
    source = git_url(modules['aap_autodeploy_configascode'])
    importers = []
    for key in selected:
        require(key in catalog, 'An unknown use-case submodule was selected.')
        entry = catalog[key]
        require('unavailable' not in entry,
                'Selected submodule %s is unavailable: %s' % (key, entry.get('unavailable', '')))
        git_url(modules[key])
        repository = repositories.get(entry['configuration'])
        git_url(repository)
        importers.append({'key': key, 'name': entry['template'],
                          'playbook': entry['playbook'], 'repository': repository})
    return {'importers': importers, 'source_project_url': source,
            'organization': protected['organization'],
            'preparation': {'name': 'Deploy Test AAP - 05 Prepare Use-Case Prerequisites',
                            'playbook': '05-prepare-use-cases.yml',
                            'repository': repositories['base']}}


def distinct_controllers(seed_instances, target_instances):
    require(isinstance(seed_instances, list) and isinstance(target_instances, list),
            'Read both controllers before starting any configuration import.')
    seed = {x.get('uuid') for x in seed_instances if isinstance(x, Mapping)}
    target = {x.get('uuid') for x in target_instances if isinstance(x, Mapping)}
    require(seed and target and None not in seed and None not in target
            and '' not in seed and '' not in target and not seed.intersection(target),
            'The fresh target and seed must have distinct verified controller instances.')
    return True


def selected_prerequisites(definitions, selected):
    require(isinstance(definitions, Mapping) and isinstance(selected, list)
            and selected and all(isinstance(key, str) and key in definitions for key in selected),
            'Select supported use cases with reviewed prerequisite definitions.')
    merged = {}
    for key in selected:
        entry = definitions[key]
        require(isinstance(entry, Mapping) and entry.get('reviewed') is True,
                'Review the selected use-case prerequisites before synchronization.')
        for repository in entry['repositories']:
            require(repository['name'] in ('rh-certified', 'validated', 'community'),
                    'Declare a supported PAH repository for every prerequisite.')
            pins = merged.setdefault(repository['name'], [])
            for pin in repository['collections']:
                if pin not in pins:
                    pins.append(pin)
    return {'reviewed': True, 'repositories': [
        {'name': name, 'collections': merged[name]}
        for name in ('rh-certified', 'validated', 'community') if merged.get(name)]}


class FilterModule:
    def filters(self):
        return {'aap_use_case_setup_plan': setup_plan,
                'aap_distinct_controllers': distinct_controllers,
                'aap_normalized_git_url': git_url,
                'aap_selected_use_case_prerequisites': selected_prerequisites}
