"""Narrow the existing native retirement plan to the selected AIOps workload."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location('aiops_teardown_filters', Path(__file__).resolve().parents[1] / 'src/aap_aiops_teardown.py')
helpers = module_from_spec(spec)
spec.loader.exec_module(helpers)


class FilterModule:
    def filters(self):
        return {'aap_aiops_teardown_authority_absent_round': helpers.authority_absent_round,
                'aap_aiops_teardown_publications_owned': helpers.publications_owned,
                'aap_aiops_teardown_inventory_variables': helpers.keys.inventory_variables,
                'aap_aiops_teardown_resources': helpers.resources,
                'aap_aiops_teardown_access': helpers.scoped_access,
                'aap_aiops_teardown_reservations': helpers.scoped_reservations}
