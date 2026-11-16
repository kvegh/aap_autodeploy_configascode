"""Read-only native proof that selected clone files have no foreign consumers.

Runs on the existing hypervisor Python, with bounded virsh/qemu-img read-only
queries. It never stops a domain, edits storage, opens a guest or follows a
selected symlink. Repeated immediately before unlink under the native lock.
"""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET


class OwnershipError(ValueError):
    pass


def require(value, message):
    if not value:
        raise OwnershipError(message)


def native(*args):
    process = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    require(process.returncode == 0 and len(process.stdout) <= 4 * 1024 * 1024,
            'A bounded native disk ownership read failed; preserve all storage.')
    return process.stdout


def xml_disks(text):
    root = ET.fromstring(text)
    paths = []
    for disk in root.findall('.//disk'):
        if disk.get('device') in ('cdrom', 'floppy'):
            continue
        source = disk.find('source')
        if source is None:
            continue
        require(set(source.attrib) <= {'file', 'index'} and bool(source.get('file')),
                'Unsupported native storage source requires review before deletion.')
        paths.append(source.get('file'))
    # Snapshot XML may have explicit backingStore chains as well as disk roots.
    for source in root.findall('.//backingStore/source'):
        require(bool(source.get('file')), 'Unreadable snapshot backing source requires review.')
        paths.append(source.get('file'))
    return paths


def prove(plan, run=native, storage=Path('/opt/vms')):
    selected = plan.get('domains')
    require(plan.get('scope') == 'aiops' and isinstance(selected, list) and len(selected) == 3,
            'Use only the exact three selected workload clones.')
    names = {item['name'] for item in selected}
    targets = {str(Path(item['disk'])) for item in selected}
    require(len(names) == len(targets) == 3 and all(Path(p).parent == storage for p in targets),
            'Selected clone paths must be exact distinct native storage files.')
    target_inodes = {}
    for path in targets:
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            continue
        require(stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode) and metadata.st_nlink == 1,
                'Selected clone storage must be a nonshared regular file.')
        target_inodes[(metadata.st_dev, metadata.st_ino)] = path
    domains = [line for line in run('virsh', '-c', 'qemu:///system', 'list', '--all', '--name').splitlines() if line]
    require(len(domains) <= 128 and len(domains) == len(set(domains)), 'Require the bounded complete domain set.')
    references = []
    for name in domains:
        for flags in ((), ('--inactive',)):
            for path in xml_disks(run('virsh', '-c', 'qemu:///system', 'dumpxml', name, *flags)):
                references.append((name, path))
        snapshots = [value for value in run('virsh', '-c', 'qemu:///system', 'snapshot-list', name, '--name').splitlines() if value]
        require(len(snapshots) <= 128, 'Require bounded complete native snapshot references.')
        for snapshot in snapshots:
            for path in xml_disks(run('virsh', '-c', 'qemu:///system', 'snapshot-dumpxml', name, snapshot)):
                references.append((name + ':snapshot', path))
    files = list(storage.iterdir())
    require(len(files) <= 512, 'Native clone directory exceeds reviewed inspection bound.')
    for path in files:
        if path.suffix in ('.qcow2', '.img', '.raw', '.disk'):
            require(not path.is_symlink(), 'A native storage symlink requires review before deletion.')
            if path.is_file():
                references.append(('unattached', str(path)))
    require(len(references) <= 1024, 'Native disk references exceed reviewed inspection bound.')
    checked = set()
    for owner, path in references:
        require(Path(path).is_absolute(), 'Native image paths must be absolute.')
        resolved = str(Path(path).resolve(strict=True))
        metadata = os.stat(path)
        inode = (metadata.st_dev, metadata.st_ino)
        direct_target = path in targets and resolved == path
        if inode in target_inodes or resolved in targets:
            require(direct_target and (owner in names or owner == 'unattached'),
                    'A preserved domain or snapshot references a selected clone disk.')
        if resolved in checked:
            continue
        checked.add(resolved)
        chain = json.loads(run('qemu-img', 'info', '--force-share', '--backing-chain', '--output=json', path))
        require(isinstance(chain, list) and 1 <= len(chain) <= 32, 'Require a bounded complete native backing chain.')
        for index, image in enumerate(chain):
            filename = image.get('filename')
            require(isinstance(filename, str) and Path(filename).is_absolute(), 'Require exact native backing filenames.')
            backing_path = str(Path(filename).resolve(strict=True))
            backing_stat = os.stat(backing_path)
            if backing_path in targets or (backing_stat.st_dev, backing_stat.st_ino) in target_inodes:
                require(index == 0 and direct_target,
                        'Another image depends on selected clone storage as a backing file.')
    return {'exclusive': True, 'selected_disks': len(targets), 'native_domains': len(domains), 'inspected_images': len(checked)}


if __name__ == '__main__':
    try:
        print(json.dumps(prove(json.load(sys.stdin))))
    except Exception:
        print('Selected storage exclusivity was not proved; preserve all clone files.', file=sys.stderr)
        raise SystemExit(1)
