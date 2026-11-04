"""Prove installer-only egress cannot silently become complete guest release."""

from copy import deepcopy
import unittest

from test_guest_release import fixture, keys
from test_guest_release_runtime import fixture as runtime_fixture, runtime


class GuestBootstrapHttpsTests(unittest.TestCase):
    def test_source_adds_only_exact_https_identity_and_preserves_all_other_grants(self):
        guest, pin, main, shared, hactar, _ = fixture(new=True)
        context = keys.guest_release_context(main, shared, guest, pin, access='bootstrap_https')
        identity = {key: guest[field] for key, field in (
            ('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))}
        expected = deepcopy(context['previous_policy'])
        expected.setdefault('https_clients', []).append(identity)
        self.assertEqual(context['desired_policy'], expected)
        self.assertNotIn(identity, context['desired_policy'].get('released_clients', []))
        for original, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            updated = keys.guest_release_inventory_capture(original, context, kind)
            self.assertEqual(keys.guest_release_inventory_capture(updated, context, kind), updated)
        changed = deepcopy(context)
        changed['desired_policy'].setdefault('released_clients', []).append(identity)
        with self.assertRaises(keys.StoreError):
            keys.guest_release_context(main, shared, guest, pin,
                {key: changed[key] for key in ('previous_policy', 'desired_policy')}, access='bootstrap_https')

    def test_runtime_requires_the_same_native_guest_proof_and_no_extra_policy_change(self):
        request, state = runtime_fixture()
        request['mode'] = 'bootstrap_https'
        identity = deepcopy(request['transition']['previous_policy']['https_clients'][0])
        request['transition']['previous_policy'].pop('https_clients')
        request['transition']['desired_policy'] = deepcopy(request['transition']['previous_policy'])
        request['transition']['desired_policy']['https_clients'] = [identity]
        state['policy'] = deepcopy(request['transition']['previous_policy'])
        self.assertTrue(runtime.plan(request, state)['changed'])
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        self.assertFalse(runtime.plan(request, state)['changed'])
        for variant in ('full-release', 'foreign-uuid', 'production-denial', 'unsupported-mode'):
            changed = deepcopy(request)
            if variant == 'full-release':
                changed['transition']['desired_policy']['released_clients'] = [identity]
            elif variant == 'foreign-uuid':
                changed['guest']['uuid'] = '99999999-2222-3333-4444-555555555555'
            elif variant == 'production-denial':
                changed['transition']['desired_policy']['protected_ipv4'] = []
            else:
                changed['mode'] = 'unrestricted'
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                runtime.plan(changed, state)


if __name__ == '__main__':
    unittest.main()
