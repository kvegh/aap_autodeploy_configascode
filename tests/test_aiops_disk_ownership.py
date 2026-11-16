"""Real temporary image paths with synthetic bounded native read results."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('disk_ownership', Path(__file__).resolve().parents[1] / 'src/aap_aiops_disk_ownership.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DiskOwnershipTests(unittest.TestCase):
    def fixture(self, folder, foreign=None, backing=None, snapshot=False):
        paths = {name: folder / (name + '.qcow2') for name in ('one', 'two', 'three', 'aap', 'golden')}
        for path in paths.values():
            path.write_bytes(b'fixture')
        plan = {'scope': 'aiops', 'domains': [{'name': name, 'disk': str(paths[name])} for name in ('one', 'two', 'three')]}
        def run(*args):
            if args[0] == 'qemu-img':
                path = args[-1]
                chain = [{'filename': path}]
                if path == str(paths['aap']) and backing:
                    chain.append({'filename': str(paths[backing])})
                elif path != str(paths['golden']):
                    chain.append({'filename': str(paths['golden'])})
                return json.dumps(chain)
            if 'list' in args:
                return 'one\ntwo\nthree\naap\n'
            if 'dumpxml' in args:
                name = args[args.index('dumpxml') + 1]
                path = paths[foreign] if name == 'aap' and foreign else paths[name]
                return '<domain><devices><disk device="disk"><source file="%s"/></disk></devices></domain>' % path
            if 'snapshot-list' in args:
                return 'saved\n' if snapshot and args[-2] == 'aap' else ''
            if 'snapshot-dumpxml' in args:
                return '<domainsnapshot><disks><disk><source file="%s"/></disk></disks></domainsnapshot>' % paths['one']
            raise AssertionError(args)
        return plan, paths, run

    def test_selected_clones_and_shared_golden_are_preserved_as_separate_owners(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            plan, paths, run = self.fixture(folder)
            result = module.prove(plan, run, folder)
            self.assertTrue(result['exclusive'])
            self.assertEqual(result['native_domains'], 4)
            self.assertTrue(all(path.exists() for path in paths.values()))

    def test_preserved_domain_direct_disk_backing_or_snapshot_stops(self):
        for options in ({'foreign': 'one'}, {'backing': 'one'}, {'snapshot': True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                plan, paths, run = self.fixture(folder, **options)
                with self.assertRaises(module.OwnershipError):
                    module.prove(plan, run, folder)
                self.assertTrue(all(path.exists() for path in paths.values()))

    def test_unattached_image_backing_reference_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            plan, paths, run = self.fixture(folder)
            extra = folder / 'unattached.qcow2'
            extra.write_bytes(b'extra')
            def wrapped(*args):
                if args[0] == 'qemu-img' and args[-1] == str(extra):
                    return json.dumps([{'filename': str(extra)}, {'filename': str(paths['one'])}])
                return run(*args)
            with self.assertRaises(module.OwnershipError):
                module.prove(plan, wrapped, folder)

    def test_selected_hardlink_or_symlink_is_never_deleted(self):
        import os
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                plan, paths, run = self.fixture(folder)
                alias = folder / 'other.qcow2'
                (alias.symlink_to(paths['one']) if symlink else os.link(paths['one'], alias))
                with self.assertRaises(module.OwnershipError):
                    module.prove(plan, run, folder)
