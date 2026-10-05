# AAP AutoDeploy Plan

## Context

We need a repeatable, fully automated way to deploy fresh AAP 2.7 instances for testing. Currently there is no automation for the AAP platform install itself — only VM provisioning (`deploy_vms.yml`) and post-install configuration (`aap_deploy/` playbooks) exist separately. This project bridges the gap: from golden image clone to a fully working AAP test instance, driven entirely by Ansible.

All playbooks and docs go in `AAP-advanced-features/aap-autodeploy/`. The VM deployment playbook stays in `automAIton`. No sensitive data (passwords, tokens, IPs, hostnames) in the repo — everything parameterized via vault.

---

## Architecture Overview

```
Golden Image (RHEL 9.8 qcow2 with YOUR_AAP_USER user, installer pre-staged)
    |
    v
[1] Clone + resize disk + virt-customize hostname + virt-install on hypervisor
    |
    v
[2] Configure DNS + certbot + nginx reverse proxy on hypervisor
    |
    v
[3] Prepare host, customize inventory, run AAP installer
    |
    v
[4] AAP config-as-code (post-install configuration)
```

---

## Deliverables

### Files in `AAP-advanced-features/aap-autodeploy/`

```
aap-autodeploy/
  01-vm-setup.yml              # Create VM from golden image
  02-infra-config.yml          # DNS, certbot, nginx reverse proxy
  03-aap-install.yml           # Prepare host + run AAP installer
  04-aap-config.yml            # AAP config-as-code (post-install)
  destroy-test-aap.yml         # Destroy a test VM
  templates/
    nginx-aap-test.conf.j2     # nginx reverse proxy config for test instance
  vars/
    main.yml                   # Non-sensitive defaults (sizing, paths)
myvars                         # Vault-encrypted secrets (repo root)
```

Playbooks 02-04 take `vm_name` and `vm_ip` as extra_vars. Playbook 01 outputs these values.

Secrets come from `myvars` in the repo root (vault-encrypted).

---

## Step-by-Step Design

### Step 1: VM Creation (`01-vm-setup.yml` — targets: hypervisor)

Clone golden image, resize disk, customize hostname, virt-install. Outputs `vm_name` and `vm_ip` for subsequent playbooks.

- VM naming pattern: `aap{{ aap_version_short }}-{{ vm_suffix }}-{{ counter }}` (e.g., `aap27-test-1`)
- The same name is used as VM name, hostname, and DNS subdomain for consistency.

### Step 2: Infrastructure Config (`02-infra-config.yml` — targets: hypervisor)

Must run before the AAP installer — the installer's Lightspeed OAuth task connects to the gateway via FQDN.

1. **GoDaddy DNS A record** — point subdomain to hypervisor's public IP
2. **Certbot** — obtain Let's Encrypt certificate for the subdomain
3. **Nginx template + reload** — reverse proxy matching existing AAP setup (HSTS, rate limit, websocket upgrade)

**Domain approach — use a subdomain**, not a path:
- AAP's Envoy gateway expects to own the domain root; path-based routing breaks it
- New subdomain: matches VM name, e.g., `aap27-test-1.{{ domain }}`
- Nginx reverse proxy is **required** — VMs are on an internal libvirt network, only the hypervisor has a public IP.

### Step 3: AAP Installation (`03-aap-install.yml` — targets: new VM)

1. **Prepare host** — wait for SSH, grow filesystem, subscribe to RHEL, install ansible-core
2. **Customize the inventory** — search-and-replace hostname from source AAP FQDN to new VM's FQDN
3. **Set bundle install vars** — add `bundle_install=true` and `bundle_dir` to inventory
4. **Run the installer** — `ansible-playbook -i inventory ansible.containerized_installer.install`
   - Takes ~30-40 minutes
   - Runs as `YOUR_AAP_USER` user (rootless podman)
5. **Verify AAP** — ping the API

The `YOUR_AAP_USER` user, sudo, linger, SSH authorized_keys, and the AAP installer bundle are all pre-staged in the golden image.

### Step 4: AAP Config-as-Code (`04-aap-config.yml` — targets: new AAP)

Post-install configuration: projects, credentials, job templates, etc.

---

## Credential & Secret Handling

All secrets live in `myvars` (vault-encrypted, in the repo root). The playbook loads it via `vars_files: [../myvars]`.

**Required variables in myvars** (same names as the current AAP inventory):

| Variable | Purpose |
|---|---|
| `registry_username` | Red Hat registry service account |
| `registry_password` | Registry service account token |
| `postgresql_admin_password` | PostgreSQL admin password |
| `gateway_admin_password` | Gateway admin password |
| `gateway_pg_password` | Gateway PostgreSQL password |
| `controller_admin_password` | Controller admin password |
| `controller_pg_password` | Controller PostgreSQL password |
| `hub_admin_password` | Hub admin password |
| `hub_pg_password` | Hub PostgreSQL password |
| `eda_admin_password` | EDA admin password |
| `eda_pg_password` | EDA PostgreSQL password |
| `automationmetrics_pg_password` | Metrics PostgreSQL password |
| `automationmetrics_controller_read_pg_password` | Metrics controller read PG password |
| `rhsm_activation_key` | RHEL subscription activation key |
| `rhsm_org_id` | RHEL subscription org ID |
| `godaddy_api_token` | GoDaddy API token for DNS records |
| `domain` | Domain name |
| `public_ip` | Hypervisor's public IP |

### `main.yml` (committed — non-sensitive defaults)

```yaml
# VM sizing
aap_vcpus: 4
aap_memory_mb: 20480
aap_disk_size: "60G"

# AAP installer
aap_version: "2.7-8"
aap_version_short: "27"   # used in naming: aap27-test-N
installer_extract_dir: "/opt/sources"

# Golden image
golden_image_path: "/opt/vms/goldimg-vm-1.disk.qcow2"

# Network
vm_network: "internal"
vm_dir: "/opt/vms"
```

---

## Key Design Decisions

1. **KISS: Single playbook, multi-play** — not a role galaxy. One `deploy-test-aap.yml` with 4 plays. Post-install AAP configuration (projects, credentials, JTs) is handled separately.

2. **Bundle install, not online** — copy the existing 3.8G tarball rather than downloading from registry. Faster, no internet dependency, reproducible.

3. **Subdomain + nginx required for external access** — VMs are on internal libvirt network, only the hypervisor has a public IP. Nginx reverse proxy is mandatory, same as the existing AAP setup. Subdomain = VM name (e.g., `aap27-test-1`).

4. **Vault for ALL secrets** — passwords, registry creds, hostnames, IPs. The repo contains zero environment-specific values.

5. **Golden image as base** — pre-updated RHEL 9.8 with `YOUR_AAP_USER` user (sudo, linger, hypervisor SSH key), and the AAP installer bundle unpacked under `/opt/sources/`. Subscribe only to enable AAP repo and install ansible-core, not for general updates.

6. **Installer pre-staged in golden image** — eliminates the slow SCP transfer step entirely. The unpacked bundle (~3.5 GiB) is baked into the golden image.

7. **Filesystem grow after clone** — golden image is small (~10G), resize to 60G at clone time, grow XFS on first boot.

8. **Strict safety assertions on all destructive operations** — every task in `destroy-test-aap.yml` that deletes, removes, or undefines a resource MUST have an `assert` immediately before it that validates the target path/name against the allowed pattern (`^aap27-test-\d+$`). This applies to: virsh destroy, virsh undefine, disk removal, nginx config removal, certbot delete, and DNS record deletion. No destructive task may rely solely on an upfront validation — each must be individually guarded. Shell injection patterns (`;`, `&&`, `|`, `$`, `` ` ``) must also be rejected.

---

## Verification

1. **VM boots**: `virsh list` on hypervisor shows new VM running
2. **SSH works**: `ansible -m ping` against new VM succeeds
3. **AAP accessible**: `curl -k https://<new-ip>` returns the AAP login page
4. **API works**: `curl -k -u admin:<password> https://<new-ip>/api/controller/v2/ping/` returns 200
5. **Post-install objects**: Job templates, credentials, projects exist in the new AAP

---

## Decisions Made

1. **No subscription manifest needed** — Red Hat defaults to SCA (Simple Content Access). The containerized installer pulls images using a registry service account (username/token in vault), not a manifest file.

2. **Full stack** — deploy all components (Gateway, Controller, EDA, Hub, MCP, Metrics) to match the production setup and support AIOps demo testing.

3. **Subdomain over path** — AAP's Envoy proxy owns the domain root, so path-based routing (`/test-vX`) won't work. Use a parameterized subdomain instead.

---

## Resolved

- **Subscription for AAP repo**: Subscribe using activation key + org ID from vault (`rhsm_activation_key`, `rhsm_org_id`), enable AAP repo, install ansible-core. System stays subscribed.
