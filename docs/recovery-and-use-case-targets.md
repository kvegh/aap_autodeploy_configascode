# Agreed recovery and use-case deployment targets

This document records the operator's agreed requirements. It does not claim that
all of them are implemented or verified. Beads holds the current task states,
blockers and verification evidence; the decision history cites implementation
commits.

## Recovery goal and acceptance

The complete hypervisor environment must be reproducible after reinstalling its
bare-metal operating system. The AAP that runs recovery may be external,
including on the operator's laptop. Recovery must not depend on an AAP VM hosted
on the machine being reinstalled.

The end-to-end success criterion is that one complete versioned environment can
install the next version, and both work independently without manual fixes. This
covers host configuration, networking, the firewall, libvirt, nginx, guest
configuration, DNS and the selected service integrations. The new environment
must also have the code, protected configuration and credential access needed to
repeat the process.

The current production hypervisor is excluded from the versioned test chain.
The acceptance criterion does not itself authorize a new allocation, another
live rebuild or destruction of the current environment.

## Existing and future AAP deployment templates

Keep the four older AAP deployment Job Templates on the existing production AAP
for now. Exclude those four from the CaC bundle used for future installations.
Future environments use the newer four-stage templates. Both sets reference the
same four files in the same public automation project:

1. `01-linux-vm-setup.yml`
2. `02-infra-config.yml`
3. `03-aap-install.yml`
4. `04-aap-config.yml`

The newer templates must support both the hypervisor hosting their source AAP
and a selected remote replacement hypervisor. They do not need to deploy onto
the current original production hypervisor. Keeping the older set is not a
reason to transfer its production Machine key to future installations.

The older workflow, destroy template, inventory and credential references must
be reviewed consistently when excluding the four stages. This does not authorize
deleting their existing production objects. Future-bundle exclusion and the
complete source-local deployment cycle remain to be verified.

The separate [older destroy-template review](legacy-decommission-review.md)
found that both destroy templates use the same current decommission playbook.
The older template adds no cleanup logic; its broader manual launch prompts are
the distinguishing behavior. Retirement is recommended but has not been applied.
Neither current configuration establishes teardown support for historical VMs
on the original production hypervisor.

## CaC installation and runtime deployment are separate choices

The shared CaC importer must support installing a use case onto the AAP running
the import or onto another explicitly selected AAP. The destination AAP may run
on the same physical hypervisor or on a remote hypervisor. Self-targeting does
not mean Ansible's `localhost`: it means using the selected AAP's verified HTTPS
API and appropriate API credentials.

Keep the agreed one-playbook design: repository-specific deployment templates
call `deploy-cac-project.yml` directly with their saved `aap_cac_project_id` and
their own repository reader and CaC Vault credentials. No wrapper playbooks,
SSH password fallback, new credential type or additional job is implied by
target selection.

After CaC installation, each use case's jobs must retain their intended runtime
target choices. A successful import only proves the definitions were installed;
it does not prove the application or demo works. Do not impose a generic
target-AAP selector on jobs where that choice is irrelevant.

For Automation Orchestrator, three locations are independent: AAP-A runs the
deployment job, the configured external OpenShift cluster receives AO, and AO
connects to selected AAP-B. AAP-B may be AAP-A or another versioned AAP. The
existing integration URL and credentials express that choice. With AAP
integration enabled, AO's OIDC setup also registers an OAuth application in the
selected AAP, so integration is not read-only.

For AIOps, setup must support its source environment or another selected
versioned environment. The destination determines hypervisor placement, VMs,
website/DNS/proxy configuration, monitoring targets, EDA bindings and private
MCP connections. URLs, credentials and restoration jobs must refer to the
intended environment. Working local behavior does not prove remote runtime
deployment.

## Recovery isolation policy

Extra recovery quarantine protects against restored images contacting production
through inherited credentials, service addresses and automation. Release an exact
guest from that additional IPv4 quarantine only after successful configuration
and identity checks. Production destinations remain explicitly blocked; the
normal firewall, private MCP policy and restrictions on other guests remain.
Live release and the existing encrypted policy/source-inventory copies must be
reconciled so later runs preserve the decision. See the
[shared guest release role](../roles/recovery_guest_release/README.md).

## Durable records

| Beads record | Decision or verification scope |
| --- | --- |
| `bead-wd-3ix` | Complete independent recovery and version-to-version acceptance |
| `bead-wd-72f.30` | Future AutoDeploy bundle, older stages and source-local/remote prerequisites |
| `bead-wd-72f.31` | Destination-specific runtime behavior for all use cases |
| `bead-wd-mcr.1` | Automatic guest release with production protection |
| `bead-wd-72f.32` | Git TODO synchronization, encrypted full records and recovery instructions |

Read the latest descriptions and notes: earlier exploratory alternatives remain
in the history, while later explicit operator decisions take precedence. Current
publication and live-validation limitations belong in those records, not in a
claim that an agreed requirement has already passed.
