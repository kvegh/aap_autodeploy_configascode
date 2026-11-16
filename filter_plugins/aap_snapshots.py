"""Fail closed on Controller/EDA schema or pagination drift before shutdown."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from ansible.errors import AnsibleFilterError

SPEC = spec_from_file_location('aap_snapshot_filters', Path(__file__).resolve().parents[1] / 'module_utils/aap_snapshot.py')
snapshots = module_from_spec(SPEC); SPEC.loader.exec_module(snapshots)


def next_page(data, origin):
    try:
        return snapshots.eda_next_page(data, origin)
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError('EDA activation state or pagination is unsafe or incomplete; no VM power operation is permitted.') from None


def controller_page(data, origin, state=None):
    try:
        return snapshots.controller_jobs_page(data, origin, state)
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError('Controller job state or pagination is unsafe or incomplete; no VM power operation is permitted.') from None


class FilterModule:
    def filters(self):
        return {'aap_snapshot_eda_next_page': next_page,
                'aap_snapshot_controller_jobs_page': controller_page}
