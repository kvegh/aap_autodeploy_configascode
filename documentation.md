# AAP AutoDeploy — Documentation

Automated deployment pipeline for AAP 2.7 test instances. Takes a RHEL 9.8 golden image and produces a fully configured AAP with all projects, credentials, job templates, EDA, and schedules.

## Pipeline

Four playbooks, run in sequence. Each is a separate AAP job template.

| Step | Playbook | Targets | What it does |
|---|---|---|---|
| 01 | `01-vm-setup.yml` | hypervisor | Clone golden image, resize disk, customize hostname, virt-install. Outputs `vm_name` and `vm_ip`. |
| 02 | `02-infra-config.yml` | hypervisor | GoDaddy DNS A record, Let's Encrypt cert, nginx reverse proxy. Must run before 03 — the AAP installer needs the FQDN reachable. |
| 03 | `03-aap-install.yml` | new VM | Grow filesystem, subscribe RHEL, install ansible-core, customize installer inventory, run containerized installer (~30-40 min). |
| 04 | `04-aap-config.yml` | localhost → new AAP API | Post-install config-as-code. Creates all AAP objects (users, credentials, projects, JTs, EDA, schedules). |

Playbooks 02-04 take `vm_name` and `vm_ip` as extra vars.

There's also `destroy-test-aap.yml` for teardown (with strict per-task safety assertions against the `aap27-test-N` naming pattern).

## Key Decisions

1. **Separate playbooks, not one monolith** — originally planned as a single multi-play playbook, split into 4 for independent AAP job template execution and easier reruns on failure.

2. **Bundle install** — the 3.5 GiB AAP installer is pre-staged in the golden image. No download at deploy time.

3. **Subdomain routing** — each test instance gets `aap27-test-N.{domain}`. AAP's Envoy gateway owns the domain root, so path-based routing doesn't work. Nginx reverse proxy is mandatory (VMs are on internal libvirt network).

4. **Golden image** — RHEL 9.8 with `YOUR_AAP_USER` user (sudo, linger, SSH keys) and the installer bundle already unpacked. Avoids repeating host prep on every deploy.

5. **Vault for all secrets** — the repo contains zero environment-specific values. Everything sensitive comes from `myvars` (vault-encrypted, repo root).

6. **Safety assertions on destroy** — every destructive task in `destroy-test-aap.yml` has an `assert` guard validating the target against `^aap27-test-\d+$`. Shell injection patterns are rejected.

7. **Config-as-Code via dispatch role** — Step 04 is being migrated to `infra.aap_configuration`'s dispatch role with per-project variable files. See [Configuration_as_Code.md](Configuration_as_Code.md).

## File Structure

```
aap-autodeploy/
    01-vm-setup.yml
    02-infra-config.yml
    03-aap-install.yml
    04-aap-config.yml            # being rewritten to use dispatch role
    destroy-test-aap.yml
    templates/
        nginx-aap-test.conf.j2
    vars/
        main.yml                 # non-sensitive defaults (VM sizing, paths)
    documentation.md             # this file (includes TODOs)
    Configuration_as_Code.md     # CaC architecture and resource inventory
    PLAN.md                      # original design plan
../myvars                        # vault-encrypted secrets (repo root)
```

## Secrets

All secrets are in `myvars` at the repo root (vault-encrypted). Loaded via `vars_files: [../myvars]`.

Two categories:
- **Infrastructure secrets** (steps 01-03): registry credentials, PostgreSQL passwords, RHSM activation key, GoDaddy API token, domain, hypervisor IP.
- **AAP object secrets** (step 04): credential inputs (SSH keys, vault passwords, PAH tokens), user passwords. These live in the CaC variable files — see [Configuration_as_Code.md](Configuration_as_Code.md).

## Current State

- Steps 01-03: working, tested end-to-end.
- Step 04: working with the current task-based approach. Migration to dispatch role pending.
- CaC files: all current AAP resources captured. 5 project groups complete, 3 skeletons.

## TODOs

### Cleanup (existing AAP instance)

- [ ] Sanitize variable names across playbooks and vault — establish a consistent naming convention (e.g., decide on `vault_` prefix vs no prefix, `password` vs `passwd`, snake_case consistently)
- [ ] Clean up duplicate credentials (ids 9, 10 — empty "hypervisor cred" entries) in AAP UI
- [ ] Clean up temp host "golden-image-temp" (host 11) from AAP inventory
- [ ] Delete temp JT 29 ("TEMP - Configure AutoDeploy JTs") from AAP UI
- [ ] Destroy leftover test VMs: aap27-test-10, aap27-test-11

### CaC migration

- [ ] Install `infra.aap_configuration` collection (needed for dispatch role)
- [ ] Rewrite `04-aap-config.yml` to use dispatch role + CaC variable files (replaces current task-per-resource approach)
- [ ] Fill CHANGEME secrets in CaC files (credential inputs, EDA credentials, Event Stream)
- [ ] Build Bitwarden backup script for secrets
- [ ] Vault-encrypt CaC files and commit to repo
- [ ] Complete skeleton CaC files: servicenow.yml, config_exceptions.yml, intelligent_assistant.yml
- [ ] Test full 01→02→03→04 pipeline with new dispatch-based 04

### CaC drift detection

- [ ] Build activity stream export — AAP's `/api/controller/v2/activity_stream/` logs every create/update/delete from day one (876 entries currently, starting from install on 2026-07-11). Parse the stream incrementally (track last processed ID) to detect UI changes and sync them back into CaC files. This avoids the fragile approach of querying each object type separately, which breaks when new types are added in AAP updates.

### Done

- [x] End-to-end test: run full sequence 01→02→03→04 (current task-based approach)
- [x] CaC files: capture all current AAP resources (base.yml + 7 project groups)
- [x] Document CaC architecture in Configuration_as_Code.md
