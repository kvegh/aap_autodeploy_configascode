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

## Order of functional verification

First prove the source environment's remaining use cases through their actual
runtime jobs and service checks. Include the selected website recovery loop,
monitoring, private MCP integrations and authorized agent-remediation tests,
alongside the other installed use cases. Successful configuration imports alone
do not establish this functional result.

After those checks pass, pause the source environment's monitoring, TRA and
testserver guests to reduce simultaneous RAM use. Keep its AAP and hypervisor
services running, and preserve the paused guests' definitions and disks for
restart. Additional guests created for Windows or Assistant tests require their
own memory accounting and an explicit place in this pause sequence.

Use the still-running source AAP to build the next AAP, install its selected CaC
and deploy and verify the next environment's services. This is itself a required
functional test of the source AAP; the complete deployment capability is proved
only after that successor works. Verify both own-hypervisor and remote-target
paths where the acceptance plan requires them.

Before executing the transition, check actual host capacity, all running guest
allocations and normal host/VM overhead. Current protected capacity evidence
belongs in the existing encrypted task records. Reclaimable cache or memory
deduplication must not be treated as guaranteed capacity for every guest's peak.
This sequence records the agreed plan; live shutdown and allocation remain
separate execution steps after their prerequisites are verified.

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
deleting their existing production objects. A normal configuration import has
now verified fourteen future AutoDeploy templates and the older family's
absence on the receiving AAP, preserving all fifty-five existing templates.
The complete source-local deployment cycle remains to be verified.

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

A fresh AIOps destination also needs its own verified guest ownership/artifacts,
target-local website/EDA credentials and encrypted runtime settings in the
existing private AIOps companion. The current capture has a prepared instance;
automatic preparation of another instance is still tracked in
`bead-wd-72f.31.2`. The ciphertext embedding helper copies prepared settings and
does not generate those new identities or credentials. Agree that lifecycle
before adding any persistence or writer mechanism.

## Recovery isolation policy

Extra recovery quarantine protects against restored images contacting production
through inherited credentials, service addresses and automation. Release an exact
guest from that additional IPv4 quarantine only after successful configuration
and identity checks. Production destinations remain explicitly blocked; the
normal firewall, private MCP policy and restrictions on other guests remain.
Live release and the existing encrypted policy/source-inventory copies must be
reconciled so later runs preserve the decision. See the
[shared guest release role](../roles/recovery_guest_release/README.md).

The generic Linux deployment's normal configuration-only job 3282 passed live
acceptance for one existing test guest. Independent checks verified the exact
saved/live policy, production denial, unchanged VM definitions and ordinary host
services, and public guest connectivity. Its three encrypted configuration
updates and source inventory also match the intended transition, with API tokens,
allocation history and existing literal template tags preserved. This verifies
that deployment path for the selected guest; the other guests remain restricted.
It does not establish release integration for every VM type or the complete
version-to-version recovery cycle.

## Durable records

| Beads record | Decision or verification scope |
| --- | --- |
| `bead-wd-3ix` | Complete independent recovery and version-to-version acceptance |
| `bead-wd-72f.30` | Future AutoDeploy bundle, older stages and source-local/remote prerequisites |
| `bead-wd-72f.31` | Destination-specific runtime behavior for all use cases |
| `bead-wd-mcr.1` | Automatic guest release with production protection |
| `bead-wd-72f.32` | Git TODO synchronization, encrypted full records and recovery instructions |
| `bead-wd-72f.33` | Missing private Claude runtime prerequisites and controlled agent repair |

Read the latest descriptions and notes: earlier exploratory alternatives remain
in the history, while later explicit operator decisions take precedence. Current
publication and live-validation limitations belong in those records, not in a
claim that an agreed requirement has already passed.
