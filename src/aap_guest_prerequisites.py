#!/usr/bin/env python3
"""Read-only checks for the existing bundled installer preparation path."""

import configparser
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import ssl
import subprocess
import sys

GIB = 1024**3
HTTPS_HOSTS = (
    "subscription.rhsm.redhat.com",
    "cdn.redhat.com",
    "registry.redhat.io",
)


def root_layout(mount, devices):
    """The preparation playbook grows exactly sda partition 4 and root XFS."""
    entries = mount.get("filesystems", [])
    root = entries[0] if len(entries) == 1 else {}
    disks = devices.get("blockdevices", [])
    disk = next((d for d in disks if d.get("name") == "sda"), {})
    partition = next(
        (p for p in disk.get("children", []) if p.get("name") == "sda4"), {}
    )
    return {
        "supported": root.get("source") == "/dev/sda4"
        and root.get("fstype") == "xfs"
        and partition.get("type") == "part",
        "disk_bytes": int(disk.get("size") or 0),
        "partition_bytes": int(partition.get("size") or 0),
        "unallocated_bytes": max(
            0,
            int(disk.get("size") or 0)
            - sum(int(p.get("size") or 0) for p in disk.get("children", [])),
        ),
        "filesystem": root.get("fstype"),
        "root_source": root.get("source"),
    }


def filesystem(path):
    values = os.statvfs(path)
    return {
        "total_bytes": values.f_blocks * values.f_frsize,
        "available_bytes": values.f_bavail * values.f_frsize,
        "shares_root": os.stat(path).st_dev == os.stat("/").st_dev,
    }


def trusted_https(host, rhsm_ca_dir=None):
    if rhsm_ca_dir is None:
        configuration = configparser.ConfigParser()
        configuration.read("/etc/rhsm/rhsm.conf")
        rhsm_ca_dir = configuration.get("rhsm", "ca_cert_dir", fallback="/etc/rhsm/ca")
    attempts = []
    for trust in ("system", "installed_rhsm_ca"):
        ca_paths = (
            sorted(Path(rhsm_ca_dir).glob("*.pem"))
            if trust == "installed_rhsm_ca"
            else []
        )
        if trust == "installed_rhsm_ca" and not ca_paths:
            break
        context = ssl.create_default_context()
        if trust == "installed_rhsm_ca":
            loaded = 0
            for path in ca_paths:
                try:
                    context.load_verify_locations(cafile=str(path))
                    loaded += 1
                except (OSError, ssl.SSLError):
                    continue
            if not loaded:
                break
        try:
            with socket.create_connection((host, 443), timeout=10) as connection:
                with context.wrap_socket(connection, server_hostname=host):
                    return {
                        "verified": True,
                        "trust": trust,
                        "failed_attempts": attempts,
                    }
        except (OSError, ssl.SSLError) as error:
            result = {"trust": trust, "error_type": type(error).__name__}
            if isinstance(error, ssl.SSLCertVerificationError):
                result["verify_code"] = getattr(error, "verify_code", None)
            elif isinstance(error, ssl.SSLError):
                result["ssl_reason"] = getattr(error, "reason", None)
            attempts.append(result)
    return {"verified": False, "failed_attempts": attempts}


def phase_assessment(checks, tools, storage, filesystems, growth_dry_run):
    """Distinguish the starting conditions from work owned by preparation."""
    preparation = {
        k: v
        for k, v in checks.items()
        if k
        not in (
            "required_tools",
            "bundle_temporary_space",
            "bundle_var_temporary_space",
        )
    }
    preparation["preparation_tools"] = all(v for k, v in tools.items() if k != "podman")
    storage_ready = (
        checks["bundle_temporary_space"] and checks["bundle_var_temporary_space"]
    )
    expansion = max(0, storage["unallocated_bytes"] - GIB)
    if storage["supported"] and growth_dry_run == 0:
        storage_ready = all(
            filesystems[path]["available_bytes"]
            + (expansion if filesystems[path]["shares_root"] else 0)
            >= needed
            for path, needed in (("/tmp", 10 * GIB), ("/var/tmp", 3 * GIB))
        )
    preparation["preparable_temporary_space"] = storage_ready
    return {
        "preparation_checks": preparation,
        "preparation_failed_checks": sorted(k for k, v in preparation.items() if not v),
        "preparation_ready": all(preparation.values()),
        "installer_ready": all(checks.values()),
        "pending_installer_tools": sorted(k for k, v in tools.items() if not v),
    }


def package_evidence(collection):
    """Report vendor ownership evidence; never infer installed packages from text."""
    result = {"podman_references": [], "package_task_paths": []}
    for path in sorted((collection / "roles").rglob("*.yml")):
        if not path.is_file() or path.stat().st_size > 256 * 1024:
            continue
        text = path.read_text()
        relative = str(path.relative_to(collection))
        if re.search(r"(?m)^[^#\n]*\bpodman\b", text):
            result["podman_references"].append(relative)
        if re.search(r"(?m)^\s*(ansible\.builtin\.)?(dnf|package):", text):
            result["package_task_paths"].append(relative)
    return result


def read_json(command):
    return json.loads(subprocess.check_output(command, text=True, timeout=15))


def inspect(extract_dir, version, install_user):
    bundle = Path(extract_dir) / (
        "ansible-automation-platform-containerized-setup-bundle-" + version + "-x86_64"
    )
    inventory = bundle / "inventory"
    collection = (
        bundle / "collections/ansible_collections/ansible/containerized_installer"
    )
    checks = {
        "bundle_directory": bundle.is_dir(),
        "bundle_inventory": inventory.is_file(),
        "bundle_content": (bundle / "bundle").is_dir()
        and any((bundle / "bundle").iterdir()),
        "installer_collection": (collection / "playbooks/install.yml").is_file(),
    }
    text = inventory.read_text() if inventory.is_file() else ""
    seed = bool(
        re.search(r"(?m)^\s*hub_seed_collections\s*=\s*(true|yes|1)\s*$", text, re.I)
    )
    memory_kib = int(
        next(
            line.split()[1]
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemTotal:")
        )
    )
    report = {"checks": checks, "bundle_version": version, "hub_seed_collections": seed}
    report["memory_bytes"] = memory_kib * 1024
    report["cpu_count"] = os.cpu_count()
    checks["minimum_memory"] = report["memory_bytes"] >= (32 if seed else 16) * 1000**3
    checks["minimum_cpus"] = report["cpu_count"] >= 4
    os_release = Path("/etc/os-release").read_text()
    checks["rhel9_x86_64"] = (
        bool(re.search(r'(?m)^ID="?rhel"?$', os_release))
        and bool(re.search(r'(?m)^VERSION_ID="?9\.', os_release))
        and os.uname().machine == "x86_64"
    )
    tools = [
        "subscription-manager",
        "dnf",
        "growpart",
        "xfs_growfs",
        "findmnt",
        "lsblk",
        "python3",
        "tar",
        "podman",
        "systemctl",
    ]
    report["tools"] = {tool: shutil.which(tool) is not None for tool in tools}
    checks["required_tools"] = all(report["tools"].values())
    layout = root_layout(
        read_json(["findmnt", "--json", "--output", "SOURCE,FSTYPE,TARGET", "/"]),
        read_json(["lsblk", "--bytes", "--json", "--output", "NAME,TYPE,SIZE,FSTYPE"]),
    )
    report["storage"] = layout
    checks["supported_root_growth_layout"] = layout["supported"]
    checks["minimum_disk_capacity"] = layout["disk_bytes"] >= 60 * 1000**3
    report["root_growth_dry_run_rc"] = None
    if layout["supported"] and report["tools"]["growpart"]:
        dry_run = subprocess.run(
            ["growpart", "-N", "/dev/sda", "4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        report["root_growth_dry_run_rc"] = dry_run.returncode

    report["filesystems"] = {
        p: filesystem(p) for p in ["/", "/tmp", "/var/tmp", extract_dir]
    }
    checks["bundle_temporary_space"] = (
        report["filesystems"]["/tmp"]["available_bytes"] >= 10 * GIB
    )
    checks["bundle_var_temporary_space"] = (
        report["filesystems"]["/var/tmp"]["available_bytes"] >= 3 * GIB
    )
    try:
        account = pwd.getpwnam(install_user)
        checks["nonroot_installer_account"] = (
            account.pw_uid != 0 and Path(account.pw_dir).is_dir()
        )
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json,os,sys;print(json.dumps([os.access(sys.argv[1],os.R_OK),"
                "os.access(sys.argv[2],os.W_OK|os.X_OK),os.access(sys.argv[3],os.W_OK|os.X_OK)]))",
                str(inventory),
                str(bundle),
                account.pw_dir,
            ],
            user=account.pw_uid,
            group=account.pw_gid,
            extra_groups=os.getgrouplist(install_user, account.pw_gid),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        checks["installer_account_access"] = all(json.loads(probe.stdout))
    except (KeyError, OSError, subprocess.SubprocessError, ValueError):
        checks["nonroot_installer_account"] = False
        checks["installer_account_access"] = False
    report["https"] = {host: trusted_https(host) for host in HTTPS_HOSTS}
    checks["trusted_redhat_https"] = all(
        v["verified"] for v in report["https"].values()
    )
    report["failed_checks"] = sorted(k for k, passed in checks.items() if not passed)
    report["vendor_package_evidence"] = package_evidence(collection)
    report.update(
        phase_assessment(
            checks,
            report["tools"],
            layout,
            report["filesystems"],
            report["root_growth_dry_run_rc"],
        )
    )
    report["ready"] = report["preparation_ready"]
    return report


if __name__ == "__main__":
    print(json.dumps(inspect(*sys.argv[1:])))
