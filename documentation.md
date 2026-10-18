# AAP AutoDeploy — Documentation

See [README.md](README.md) for current status, setup, empty CaC templates, and
the project version policy. Older completion notes below describe earlier runs.

Automated deployment pipeline for AAP 2.7 test instances. Takes a RHEL 9.8 golden image and produces a fully configured AAP with all projects, credentials, job templates, EDA, and schedules.

## Pipeline

Four playbooks, run in sequence. Each is a separate AAP job template.

| Step | Playbook | Targets | What it does |
|---|---|---|---|
| 01 | `01-linux-vm-setup.yml` | hypervisor | Clone golden image, resize disk, customize hostname, virt-install. Outputs `vm_name` and `vm_ip`. |
| 02 | `02-infra-config.yml` | hypervisor | GoDaddy DNS A record, Let's Encrypt cert, nginx reverse proxy. Must run before 03 — the AAP installer needs the FQDN reachable. |
| 03 | `03-aap-install.yml` | new VM | Grow filesystem, subscribe RHEL, install ansible-core, customize installer inventory, run containerized installer (~30-40 min). |
| 04 | `04-aap-config.yml` | localhost → new AAP API | Post-install config-as-code. Creates all AAP objects (users, credentials, projects, JTs, EDA, schedules). |

Playbooks 02 and 03 take `vm_name` and `vm_ip` as extra vars. Playbook 04 instead
requires an explicit `aap_hostname` HTTPS URL and `aap_config_repo_url`. It does
not use `vm_name` or `vm_ip` and has no domain-based fallback.

There's also `destroy-test-aap.yml` for teardown (with strict per-task safety assertions against the `aap27-test-N` naming pattern).

## Key Decisions

1. **Separate playbooks, not one monolith** — originally planned as a single multi-play playbook, split into 4 for independent AAP job template execution and easier reruns on failure.

2. **Bundle install** — the 3.5 GiB AAP installer is pre-staged in the golden image. No download at deploy time.

3. **Subdomain routing** — each test instance gets `aap27-test-N.{domain}`. AAP's Envoy gateway owns the domain root, so public access uses hostname-based nginx routing. Stage 04 can connect directly through an internal hostname or IP supplied in `aap_hostname`; that configuration traffic does not require the public reverse proxy. Stage 03 still uses the VM's fully qualified hostname for installation, which can resolve internally.

4. **Golden image** — RHEL 9.8 with the AAP service account (`vault_aap_install_user`; sudo, linger, SSH keys) and the installer bundle already unpacked. Avoids repeating host prep on every deploy.

5. **Vault for all secrets** — the repo contains zero environment-specific values. Everything sensitive comes from `myvars` (vault-encrypted, repo root).

6. **Safety assertions on destroy** — every destructive task in `destroy-test-aap.yml` has an `assert` guard validating the target against `^aap27-test-\d+$`. Shell injection patterns are rejected.

7. **Config-as-Code via dispatch role** — Step 04 downloads the private configuration repository's `main` branch, loads its encrypted shared base, and uses `infra.aap_configuration`'s dispatch role to apply it. Demo selection remains planned. See [Configuration_as_Code.md](Configuration_as_Code.md).

## File Structure

```
aap_autodeploy_configascode/
    01-linux-vm-setup.yml
    02-infra-config.yml
    03-aap-install.yml
    04-aap-config.yml            # dispatch role against the new instance
    destroy-test-aap.yml
    restore-windows-config.yml   # Windows objects only, onto a provisioned AAP
    cac/
        base_CaC_vault.yml.example # empty shared CaC template
        project.yml.example        # empty per-demo CaC template
    templates/
        nginx-aap-test.conf.j2
        nginx-aap-test-http.conf.j2
    utils/
        tag_jts.yml
    vars/
        main.yml                 # non-sensitive defaults (VM sizing, paths)
    documentation.md             # this file (includes TODOs)
    Configuration_as_Code.md     # CaC architecture and resource inventory
    PLAN.md                      # original design plan
    myvars                       # vault-encrypted secrets (repo root)
```

## Secrets

Infrastructure and AAP access secrets are in `myvars` at the repo root
(vault-encrypted), loaded via `vars_files`. Object secrets live in encrypted
CaC files in the separate private configuration repository. Editable configuration
and Vault password files, including `vpf`, stay outside Git.

Step 04 additionally requires a custom credential injecting `CAC_GIT_TOKEN` and a
Vault credential with identifier `cac` to decrypt private CaC. Its repository URL
is the `aap_config_repo_url` extra variable; the branch is always `main` and the
shared file is `cac/base_CaC_vault.yml`. Keep the original/default `myvars` Vault
credential attached too. See [README.md](README.md#stage-04-inputs) for full inputs
and the Git/TLS requirements.

Two categories:
- **Infrastructure secrets** (steps 01-03): registry credentials, PostgreSQL passwords, RHSM activation key, GoDaddy API token, domain, hypervisor IP.
- **AAP object secrets** (step 04): credential inputs (SSH keys, vault passwords, PAH tokens), user passwords. These live in the CaC variable files — see [Configuration_as_Code.md](Configuration_as_Code.md).

## Current State

- Steps 01-03 exist; historical testing predates the repository split.
- Step 04 downloads and decrypts the private shared base before dispatch, using
  the Git-token and `cac` Vault credentials. It still uses `myvars` for environment
  and target authentication; installer-password bootstrap and password rotation
  are not implemented. Dependencies and target authentication require verification.
- The encrypted shared base is committed in the private configuration repository.
  Empty examples remain under this repository's `cac/`; editable populated
  configuration stays outside Git.
- The current full pipeline has not been verified end to end since the split.

## TODOs

### Reusable job inputs

- [ ] Redesign and document job inputs so other operators can run each stage independently. Prefer established collection input names where available; require provisioning-specific values such as `vm_name` only in stages that need them.
- [x] Require an explicit `aap_hostname` URL for Step 04, without `vm_name` or a derived domain URL.
- [ ] Make Step 04's target authentication independently configurable, removing its remaining `myvars` dependency.

### Cleanup (existing AAP instance)

- [ ] Sanitize variable names across playbooks and vault — establish a consistent naming convention (e.g., decide on `vault_` prefix vs no prefix, `password` vs `passwd`, snake_case consistently)
- [ ] Clean up duplicate credentials (ids 9, 10 — empty "hypervisor cred" entries) in AAP UI
- [ ] Clean up temp host "golden-image-temp" (host 11) from AAP inventory
- [ ] Delete temp JT 29 ("TEMP - Configure AutoDeploy JTs") from AAP UI
- [ ] Destroy leftover test VMs: aap27-test-10, aap27-test-11

### CaC migration

- [ ] Install `infra.aap_configuration` collection (needed for dispatch role)
- [x] Load shared configuration from the private configuration repository's `main` branch
- [ ] Add selection and loading of per-demo CaC alongside shared base configuration
- [ ] Fill CHANGEME secrets in CaC files (credential inputs, EDA credentials, Event Stream)
- [ ] Build Bitwarden backup script for secrets
- [ ] Vault-encrypt completed demo files, verify them, and commit/push to the private configuration repository
- [ ] Complete skeleton CaC files: servicenow.yml, config_exceptions.yml, intelligent_assistant.yml
- [ ] Test full 01→02→03→04 pipeline with new dispatch-based 04

### CaC drift detection

- [ ] Build activity stream export — AAP's `/api/controller/v2/activity_stream/` logs every create/update/delete from day one (876 entries currently, starting from install on 2026-07-11). Parse the stream incrementally (track last processed ID) to detect UI changes and sync them back into CaC files. This avoids the fragile approach of querying each object type separately, which breaks when new types are added in AAP updates.

### Done

- [x] Historical end-to-end test: full sequence 01→02→03→04 with the earlier task-based approach
- [x] Replace Step 04's task-based implementation with the dispatch role
- [x] CaC files: capture all current AAP resources (base_CaC_vault.yml + 7 project groups)
- [x] Document CaC architecture in Configuration_as_Code.md
