# AAP AutoDeploy Plan

The design below includes historical planning. See [README.md](README.md) for
the current implementation and credential handling.

## Main goal

Deploy a fresh AAP that can take over all production AAP tasks from versioned
configuration and encrypted secret inputs. The replacement must also be able to
deploy and configure further AAP instances. An existing trusted AAP provides the
initial seed; its first Git token and CaC Vault password are supplied independently.
Selected demo deployments continue to use their separate configurations.

## TODO

- [ ] Define and verify the complete production configuration inventory across
  Gateway, Controller, EDA and PAH, including ownership, credentials, permissions,
  dependencies and deletions. Preserve separate base and use-case ownership.
- [ ] Capture and redeploy Intelligent Assistant/Lightspeed through CaC, including
  installer/service settings, LLM credentials, database and service passwords,
  and Gateway OAuth configuration. Vault sensitive inputs and independently
  verify a fresh rebuild.
- [x] Implement persistent MCP access in base: create a target-local administrator
  token with write scope after administrator-password verification. Save its
  recoverable value in protected root-owned storage on the target, verify and
  preserve it on reruns, and preserve existing manually created access.
- [ ] Verify persistent MCP provisioning and reruns through a live base deployment.
  Offline API tests establish task behavior; no live rollout is claimed.
- [ ] Save generated per-instance MCP connection values, including the token,
  endpoint and CA trust material, as fully CaC-Vault-encrypted files in the private
  base configuration repository. Use opaque instance identifiers in filenames,
  verify encryption before uploading, and protect secret tasks with `no_log`.
  Provision a separate fine-grained Git write credential limited to that repository
  with Contents read/write; preserve the existing read credentials. Allow trusted
  clients to decrypt the saved values into protected local configuration outside
  Git, with certificate verification enabled. An API-masked AAP credential alone
  is not a recoverable token copy. The implemented interim copy is a private
  root-owned file on its target; encrypted Git write-back, client setup and
  controlled rotation remain pending.
- [ ] Provision the trusted replacement's bootstrap Git and Vault credentials
  from the encrypted base. Stored credential inputs alone do not create those
  objects; the first seed still needs independently supplied access.
- [ ] Restore this deployment project's own projects, inventories, credential
  types, credentials, Job Templates, surveys and workflows so the replacement
  can deploy and configure further AAP instances. Rebuild target-specific URLs,
  references and generated access tokens for the new instance.
- [ ] Automate variable handoff and ordering between deployment, base, PAH
  preparation and use-case import jobs, including resumable failure handling.
- [ ] Verify production replacement with configuration comparison and functional
  platform/use-case tests, including its ability to deploy another AAP. Treat
  external environment services as explicit prerequisites until their separate
  recreation work is implemented.
- [ ] Define and test controlled takeover of schedules, EDA activations and other
  automatic production triggers, including rollback, so a replacement can assume
  the intended work without duplicate production execution.
- [x] Implement desired administrator-password management in encrypted base
  configuration, including installer bootstrap and protected password handling.
- [x] Verify the administrator-password rollout and subsequent rerun after the
  repaired base Git credential. Jobs 2125 and 2128 succeeded; the rerun used the
  configured login and skipped installer bootstrap.
- [ ] Write and verify a step-by-step Configuration as Code guide, from a fresh
  checkout to a configured AAP. Cover prerequisites; copying and completing the
  base and use-case templates; object ownership and dependencies; private Git
  access and bootstrap credentials; Vault encryption and AAP credential setup;
  subscription and base deployment; PAH repository setup without synchronization;
  each use case's collection requirements and later PAH preparation; deployment
  Job Templates and their inputs; validation, updates, deletions, and recovery.
- [x] Implement the base PAH component: configure certified, validated, and
  community remotes, repositories, distributions, and Controller organization
  sources using local PAH credentials. Do not synchronize content or attach a
  direct public Galaxy source during base deployment.
- [x] Verify the implemented base PAH setup on a deployed target, including
  token preservation on rerun, ordered local sources, and no content sync.
- [ ] Populate and verify the PAH requirements component in each existing use-case
  configuration, including collection versions, dependencies, and compatibility
  with its execution environment, before running the use case's automation.
- [ ] Keep the number of retained PAH collection versions small for simplicity.
  Derive the exact versions to synchronize from project and execution-environment
  requirements and their dependency constraints, and declare that required set in
  the PAH CaC configuration and remote requirements. Retain multiple versions of a
  collection only when projects explicitly require them, including dependency
  requirements. For collections without a fixed project requirement, select one
  current compatible version. Audit requirements before pruning older versions,
  and prevent unbounded version selection from downloading release histories.
  Manage remote `sync_highest_versions: 1` separately from repository snapshot
  `retain_repo_versions: 1`. Add supported module/API handling for the remote
  limit, which the installed `ansible.hub.collection_remote` module does not
  expose. Encode exact pins and their dependency closure in the encrypted CaC
  configuration, preserving older versions explicitly required by projects.
- [x] Perform a reviewed one-time PAH cleanup: reduce 263 collection releases to
  16 across 15 collections, keeping each newest present release and the older
  RHEL system roles version explicitly pinned by projects. Set all three remote
  `sync_highest_versions` limits to one, pin the complete dependency closure, and
  verify repository snapshot retention remains one. Declarative enforcement in
  encrypted CaC and recurring selection/cleanup remain separate TODOs above.
- [x] Prepare Assistant Team's declared PAH collection and existing execution image,
  import the six ordinary templates and supporting objects, and independently
  verify the configuration. Runtime tests and optional authentication maintenance
  remain separate work.

## Context

We need a repeatable, fully automated way to deploy fresh AAP 2.7 instances for testing. Currently there is no automation for the AAP platform install itself — only VM provisioning (`deploy_vms.yml`) and post-install configuration (`aap_deploy/` playbooks) exist separately. This project bridges the gap: from golden image clone to a fully working AAP test instance, driven entirely by Ansible.

All playbooks and docs go in `AAP-advanced-features/aap-autodeploy/`. The VM deployment playbook stays in `automAIton`. No sensitive data (passwords, tokens, IPs, hostnames) in the repo — everything parameterized via vault.

---

## Architecture Overview

```
Golden Image (RHEL 9.8 qcow2 with the AAP service account (`vault_aap_install_user`), installer pre-staged)
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
  01-linux-vm-setup.yml              # Create VM from golden image
  02-infra-config.yml          # DNS, certbot, nginx reverse proxy
  03-aap-install.yml           # Prepare host + run AAP installer
  04-aap-config.yml            # AAP config-as-code (post-install)
  destroy-test-aap.yml         # Destroy a test VM
  templates/
    nginx-aap-test.conf.j2     # nginx reverse proxy config for test instance
  vars/
    main.yml                   # Non-sensitive defaults (sizing, paths)
  myvars                       # Vault-encrypted secrets (repo root)
```

Playbooks 02-04 take `vm_name` and `vm_ip` as extra_vars. Playbook 01 outputs these values.

Secrets come from `myvars` in the repo root (vault-encrypted).

---

## Step-by-Step Design

### Step 1: VM Creation (`01-linux-vm-setup.yml` — targets: hypervisor)

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
   - Runs rootless podman as the AAP service account (`vault_aap_install_user`)
5. **Verify AAP** — ping the API

The AAP service account (`vault_aap_install_user`), sudo, linger, SSH authorized_keys, and the AAP installer bundle are all pre-staged in the golden image.

### Step 4: AAP Config-as-Code (`04-aap-config.yml` — targets: new AAP)

Post-install configuration: projects, credentials, job templates, etc.

---

## Credential & Secret Handling

All secrets live in `myvars` (vault-encrypted, in the repo root). The playbook loads it via `vars_files: [myvars]`.

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
golden_image_path: "/opt/images/goldimg-vm-1.disk.qcow2"

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

5. **Golden image as base** — pre-updated RHEL 9.8 with the AAP service account (`vault_aap_install_user`; sudo, linger, hypervisor SSH key), and the AAP installer bundle unpacked under `/opt/sources/`. Subscribe only to enable AAP repo and install ansible-core, not for general updates.

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

1. **Separate installation access from AAP activation** — SCA and registry credentials cover RHEL/content access during installation. AAP activation is separate: Step 04 imports a complete subscription manifest from the private repository's Vault-encrypted `cac/manifest.zip.vault` before applying configuration.

2. **Full stack** — deploy all components (Gateway, Controller, EDA, Hub, MCP, Metrics) to match the production setup and support AIOps demo testing.

3. **Subdomain over path** — AAP's Envoy proxy owns the domain root, so path-based routing (`/test-vX`) won't work. Use a parameterized subdomain instead.

---

## Resolved

- **Subscription for AAP repo**: Subscribe using activation key + org ID from vault (`rhsm_activation_key`, `rhsm_org_id`), enable AAP repo, install ansible-core. System stays subscribed.
