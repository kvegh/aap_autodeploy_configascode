# AutoDeploy tasks

Beads is authoritative. This generated overview includes only sanitized task metadata.
Full selected AutoDeploy and hypervisor task records, decisions and comments are
preserved in the separate Ansible Vault-encrypted recovery export. Refresh both
outputs together with `python3 scripts/sync_todo.py --snapshot-file <protected-export> --vault-password-file <existing-password-file>`;
add `--check` to detect stale output without writing. Review public titles before committing.

Scope, notes, acceptance criteria, outcomes, comment bodies and personal metadata
are excluded here. Hypervisor-only tasks remain in that project's own overview.
See [object ownership and label coverage](docs/cac-object-ownership.md) and
[recovery and use-case targets](docs/recovery-and-use-case-targets.md) for agreed design context.

132 tasks: 27 outstanding; 105 closed.

## Outstanding tasks

| Task | Title | Status | Priority | Type | Parent / dependency IDs |
|---|---|---|---|---|---|
| bead-wd-1rl.40 | Deploy Command Center from AAP to the selected workstation | in_progress | P1 | task | bead-wd-1rl |
| bead-wd-3ix | Prove Hactar recovery on an isolated separate target | open | P1 | task | bead-wd-105, bead-wd-4s4, bead-wd-5fm, bead-wd-86z, bead-wd-a68, bead-wd-c5x, bead-wd-hny, bead-wd-pn3 |
| bead-wd-3ix.1 | Verify final test-host cleanup and fresh AAP rebuild readiness | in_progress | P1 | task | bead-wd-3ix, bead-wd-72f.31.6 |
| bead-wd-3ix.1.5 | Finish host bootstrap after conversion outlived AAP timeout | blocked | P1 | bug | bead-wd-3ix.1 |
| bead-wd-3ix.1.6 | Assess Vault password printed by diagnostic parsing | deferred | P1 | bug | bead-wd-3ix.1 |
| bead-wd-72f | Complete portable AAP and use-case deployment | open | P1 | task | — |
| bead-wd-72f.16 | Safely decommission and rebuild AAP on the replacement hypervisor | in_progress | P1 | task | bead-wd-72f, bead-wd-72f.31.2 |
| bead-wd-72f.31 | Verify destination-specific runtime configuration for every use case | in_progress | P1 | feature | bead-wd-72f |
| bead-wd-72f.31.2 | Prepare AIOps configuration for each new instance | in_progress | P1 | feature | bead-wd-72f.31 |
| bead-wd-72f.31.2.4 | Add CloudCLI user setup to AIOps CaC | open | P1 | feature | bead-wd-72f.31.2 |
| bead-wd-72f.31.2.5 | Capture external user AAP MCP token in AIOps CaC and deployment | in_progress | P1 | task | bead-wd-72f.31.2 |
| bead-wd-72f.34 | Replace custom helpers and deployed state files with Ansible and CaC | open | P1 | task | bead-wd-72f |
| bead-wd-mcr.1.1 | Complete successful-deployment release and exact-guest cleanup | in_progress | P1 | task | bead-wd-mcr.1 |
| bead-wd-1rl.40.6 | Add separate CCNG infrastructure playbook and CaC job | in_progress | P2 | task | bead-wd-1rl.40 |
| bead-wd-72f.13 | Replace temporary AAP instance token store with an external secret manager | open | P2 | feature | bead-wd-72f |
| bead-wd-72f.2 | Route extraction credentials per repository before any CaC rekey | open | P2 | task | bead-wd-72f |
| bead-wd-72f.24 | Review legacy project settings in shared AutoDeploy inventory | open | P2 | task | bead-wd-72f |
| bead-wd-72f.31.12 | Track Command Center and MCP DNS and nginx configuration in CaC | in_progress | P2 | task | bead-wd-72f.31 |
| bead-wd-72f.31.5 | Verify Automation Orchestrator against a disposable OpenShift cluster | deferred | P2 | task | bead-wd-72f.31 |
| bead-wd-72v | Design complete CaC object ownership beyond labels | open | P2 | feature | — |
| bead-wd-b3j | Rebuild Assistant CLI containers on UBI 10 | deferred | P2 | task | — |
| bead-wd-mcr | Rebuild VMs and services from CaC instead of saved system disks | open | P2 | feature | — |
| bead-wd-mcr.1 | Lift recovery isolation gradually for CaC-rebuilt VMs | in_progress | P2 | task | bead-wd-mcr |
| bead-wd-sc8 | Replace the temporary instance registry with a real CMDB | open | P2 | feature | — |
| bead-wd-72f.31.6.5.1 | Evaluate prebuilt container images and a separate build host | deferred | P3 | task | bead-wd-72f.31.6.5 |
| bead-wd-9ezo | Add External CloudCLI as an independent CaC project | deferred | P3 | task | — |
| bead-wd-x9a | Consider automating AAP updates | open | P3 | task | — |

## Tasks already done/implemented/decided against

| Task | Title | Status | Priority | Type | Parent / dependency IDs |
|---|---|---|---|---|---|
| bead-wd-1rl.40.1 | Install CCNG prerequisites on the selected test workstation | closed | P1 | task | bead-wd-1rl.40 |
| bead-wd-1rl.40.2 | Configure HTTPS reverse proxy for the existing Command Center instance | closed | P1 | task | bead-wd-1rl.40 |
| bead-wd-1rl.40.3 | Integrate Command Center through the shared AAP CaC importer | closed | P1 | task | bead-wd-1rl.40 |
| bead-wd-1rl.40.4 | Choose the project for the fresh test Command Center | closed | P1 | decision | bead-wd-1rl.40 |
| bead-wd-2i1 | Separate AIOps CaC into its private companion repository | closed | P1 | task | — |
| bead-wd-3ix.1.2 | Fix existing external-controller teardown for successor ownership records | closed | P1 | bug | bead-wd-3ix.1 |
| bead-wd-3ix.1.3 | Fix final access retirement after normal decommission | closed | P1 | bug | bead-wd-3ix.1 |
| bead-wd-3ix.1.4 | Verify reinstalled Ng hardware against encrypted CaC | closed | P1 | feature | bead-wd-3ix.1 |
| bead-wd-4lh | Diagnose failed AIOps setup and startup delay on the new test platform | closed | P1 | bug | — |
| bead-wd-63i | Declare approved optional HTTPS isolation in AutoDeploy guards | closed | P1 | task | — |
| bead-wd-72f.1 | Split per-repository CaC Vault credentials and rename all CaC Git readers | closed | P1 | feature | bead-wd-72f |
| bead-wd-72f.11 | Publish deployed AAP API access using the existing shared MCP token | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.12 | Diagnose AIOps CaC deployment failure on test instance | closed | P1 | bug | bead-wd-72f |
| bead-wd-72f.14 | Apply the agreed numbered AAP DNS naming scheme | closed | P1 | bug | bead-wd-72f |
| bead-wd-72f.15 | Deploy the versioned AIOps website on the selected recovery hypervisor | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.15.1 | Deploy the Linux and Zabbix MCP servers on the new TRA VM | closed | P1 | task | bead-wd-72f.15 |
| bead-wd-72f.16.1 | Prove source AAP deploys its successor on the test hypervisor | closed | P1 | task | bead-wd-72f.16 |
| bead-wd-72f.17 | Deploy versioned Zabbix VM and AIOps monitoring on the replacement hypervisor | closed | P1 | feature | bead-wd-72f, bead-wd-72f.16 |
| bead-wd-72f.18 | Deploy versioned testserver1 and TRA Linux VMs on the recovery hypervisor | closed | P1 | task | bead-wd-72f, bead-wd-72f.16 |
| bead-wd-72f.18.1 | Verify current VM SSH and sudo access to the replacement TRA guest | closed | P1 | task | bead-wd-72f.18 |
| bead-wd-72f.18.2 | Stage signed offline runtime packages and MCP images for the replacement TRA guest | closed | P1 | task | bead-wd-72f.18 |
| bead-wd-72f.19 | Deploy Linux MCP on TRA for the matching testserver | closed | P1 | task | bead-wd-72f.15.1, bead-wd-72f.18 |
| bead-wd-72f.20 | Deploy Zabbix MCP on TRA for the matching Zabbix instance | closed | P1 | task | bead-wd-72f.15.1, bead-wd-72f.17, bead-wd-72f.18 |
| bead-wd-72f.21 | Diagnose the fresh AAP platform MCP endpoint returning HTTP405 | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.22 | Audit non-AAP configuration in AutoDeploy secrets | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.23 | Separate AIOps configuration from AutoDeploy secrets | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.26 | Automate each AAP instance connection to its hypervisor | closed | P1 | feature | bead-wd-72f |
| bead-wd-72f.27 | Deploy Assistant Team CaC to the current test AAP | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.28 | Deploy Disconnected Windows Patching CaC to the current test AAP | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.29 | Deploy Automation Orchestrator CaC to the current test AAP | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.3 | Analyse consolidation of all AAP use-case deployment playbooks | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.30 | Deploy AAP AutoDeploy CaC to the current test AAP | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.30.1 | Refresh bootstrap credentials before importing updated AutoDeploy definitions | closed | P1 | bug | bead-wd-72f.30 |
| bead-wd-72f.31.1 | Assess v16 runtime test prerequisites and targets | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.10 | Retire previous AAP only after Windows cleanup | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.11 | Preserve MCP artifacts offhost before test hypervisor reinstall | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.2.1 | Expose the existing minimal Linux provisioning template on the successor | closed | P1 | task | bead-wd-72f.31.2 |
| bead-wd-72f.31.2.2 | Publish verified Linux SSH fields required by AIOps guest import | closed | P1 | bug | bead-wd-72f.31.2 |
| bead-wd-72f.31.2.3 | Allow MCP installer to use the existing hypervisor SSH key | closed | P1 | task | bead-wd-72f.31.2 |
| bead-wd-72f.31.3 | Prepare and verify Assistant Team on the selected test environment | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.4 | Prepare and verify Windows patching on the selected test environment | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.4.1 | Approve and add NTFS inspection support on the test hypervisor | closed | P1 | task | bead-wd-72f.31.4 |
| bead-wd-72f.31.4.2 | Complete Windows lab teardown using the existing jobs | closed | P1 | task | bead-wd-72f.31.4 |
| bead-wd-72f.31.4.3 | Restore test AAP API responsiveness after Windows region configuration | closed | P1 | bug | bead-wd-72f.31.4 |
| bead-wd-72f.31.4.5 | Fix Windows completion checks after evaluation activation | closed | P1 | task | bead-wd-72f.31.4 |
| bead-wd-72f.31.4.5.1 | Pin the production Windows project to its tested revision | closed | P1 | task | bead-wd-72f.31.4.5 |
| bead-wd-72f.31.4.6 | Approve temporary source AAP outage for successor Windows testing | closed | P1 | task | bead-wd-72f.31.4 |
| bead-wd-72f.31.4.7 | Diagnose and fix Windows VM creation release failure | closed | P1 | bug | bead-wd-72f.31.4 |
| bead-wd-72f.31.6 | Prepare and apply fresh successor use-case configuration | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.6.2 | Allow reviewed EE-based use cases without PAH repository prerequisites | closed | P1 | bug | bead-wd-72f.31.6 |
| bead-wd-72f.31.6.3 | Include the selected AAP issuer in Windows CaC trust | closed | P1 | bug | bead-wd-72f.31.6 |
| bead-wd-72f.31.6.4 | Fix the successor monitoring guest website connection | closed | P1 | bug | bead-wd-72f.31.6 |
| bead-wd-72f.31.6.4.1 | Choose how Hactar retains applied application firewall permissions | closed | P1 | decision | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.4.2 | Choose the Ansible firewall transaction lock | closed | P1 | decision | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.4.3 | Move application firewall grants into per-instance CaC | closed | P1 | task | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.4.4 | Wire native firewall inputs into use-case CaC jobs | closed | P1 | task | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.4.5 | Choose when fresh Zabbix VM details enter AIOps CaC | closed | P1 | decision | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.4.6 | Save verified new Zabbix VM details into existing CaC definitions | closed | P1 | task | bead-wd-72f.31.6.4 |
| bead-wd-72f.31.6.5 | Build MCP containers on the target during deployment | closed | P1 | feature | bead-wd-72f.31.6 |
| bead-wd-72f.31.8 | Prepare successor Assistant test settings without replacing predecessor data | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.31.9 | Run successor Assistant software test and owned retirement | closed | P1 | task | bead-wd-72f.31 |
| bead-wd-72f.32 | Synchronize recovery tasks and decisions into Git | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.33.1 | Add Claude installation with private Linux and Zabbix MCP setup | closed | P1 | feature | bead-wd-72f.33 |
| bead-wd-72f.34.1 | Inventory JSON and custom state deployed on managed servers | closed | P1 | task | bead-wd-72f.34 |
| bead-wd-72f.35 | Map the last 24 hours of project decisions, actions and delays | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.36 | Map seven days of project decisions, actions and delays | closed | P1 | task | bead-wd-72f |
| bead-wd-72f.37 | Diagnose stalled subagent tool calls and restore reliable worker status | closed | P1 | bug | bead-wd-72f |
| bead-wd-72f.4 | Verify and correct disabled EDA activation semantics before importer migration | closed | P1 | bug | bead-wd-72f |
| bead-wd-72f.5 | Implement project-ID-based generic CaC deployment | closed | P1 | feature | bead-wd-72f |
| bead-wd-72f.5.1 | Rename all five CaC captures and migrate repository references | closed | P1 | task | bead-wd-72f.5 |
| bead-wd-72f.5.2 | Consolidate CaC importers and retarget five production Job Templates | closed | P1 | feature | bead-wd-72f.5 |
| bead-wd-72f.5.3 | Apply project-derived deployment JT names everywhere after consolidation | closed | P1 | task | bead-wd-72f.5, bead-wd-72f.5.1, bead-wd-72f.5.2 |
| bead-wd-8di | Audit registered guest installation prerequisites before AAP install | closed | P1 | task | — |
| bead-wd-8lc | Add preview and three-way encrypted CaC update automation | closed | P1 | feature | bead-wd-9yq |
| bead-wd-9kn | Add inventory VM-to-hypervisor groups for use-case target selection | closed | P1 | feature | — |
| bead-wd-9yq | Refresh autodeploy CaC template labels and newly defined jobs | closed | P1 | task | — |
| bead-wd-bld | Reconcile cloned Zabbix and verify website EDA recovery | closed | P1 | feature | bead-wd-x7k |
| bead-wd-c65 | Reserve test AAP names in shared encrypted allocation state | closed | P1 | feature | — |
| bead-wd-euh | Refresh AutoDeploy DNS token from current authorized Hactar Vault | closed | P1 | task | — |
| bead-wd-fmk | Repair literal injector tags in optional CaC captures | closed | P1 | bug | bead-wd-qyc |
| bead-wd-nld | Diagnose Zabbix reaction to the website test | closed | P1 | task | — |
| bead-wd-nt3 | Verify and test Zabbix agent deployment on the new testserver | closed | P1 | task | — |
| bead-wd-qyc | Fix actual fresh AAP base configuration variable merge failure | closed | P1 | bug | — |
| bead-wd-sur | Propagate verified seed CA trust for selected AIOps configuration setup | closed | P1 | bug | — |
| bead-wd-x7k | Preserve running EDA activations during repeat CaC import | closed | P1 | bug | — |
| bead-wd-xzi | Confirm public AAP access policy and future-only TLS scope | closed | P1 | task | — |
| bead-wd-xzi.1 | Verify upstream TLS for future AAP deployments only | closed | P1 | bug | bead-wd-xzi |
| bead-wd-1rl.40.5 | Choose backend certificate prerequisite order for fresh CCNG deployment | closed | P2 | decision | bead-wd-1rl.40 |
| bead-wd-2uk | Compare production and test website launch settings | closed | P2 | task | — |
| bead-wd-3ix.1.1 | Declare jq for rebuilt hypervisor cleanup | closed | P2 | task | bead-wd-3ix.1 |
| bead-wd-72f.10 | Use existing Git credential type for the dedicated allocation writer | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.25 | Rename the new AAP inventory host after AIOps import | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.31.4.4 | Assess Windows runtime configuration for the fresh successor | closed | P2 | task | bead-wd-72f.31.4 |
| bead-wd-72f.31.6.1 | Apply the corrected prerequisite survey to both AAP instances | closed | P2 | task | bead-wd-72f.31.6 |
| bead-wd-72f.31.7 | Assess Assistant Team deployment readiness on the fresh successor | closed | P2 | task | bead-wd-72f.31 |
| bead-wd-72f.33 | Prepare the private Claude runtime and verify agent remediation | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.6 | Review AutoDeploy allocator and registry credential design with owner | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.7 | Prefix project deployment Job Template names with Deploy | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.8 | Reuse AutoDeploy CaC Vault credential for registry encryption and decryption | closed | P2 | task | bead-wd-72f |
| bead-wd-72f.9 | Reuse AutoDeploy repository read token for registry reads | closed | P2 | task | bead-wd-72f |
| bead-wd-b3t | Store explicit AAP FQDNs in the shared host inventory | closed | P2 | task | — |
| bead-wd-ddq | Disable website launch-variable prompt in CaC | closed | P2 | task | — |
| bead-wd-j0g.8 | Register RHEL CaC deployment with the shared importer and JT | closed | P2 | feature | bead-wd-j0g |
| bead-wd-wgn | Verify AutoDeploy infrastructure prerequisites from Hactar base | closed | P2 | task | — |
| bead-wd-zau | Review copied testserver monitoring and agent remediation readiness | closed | P2 | task | — |
