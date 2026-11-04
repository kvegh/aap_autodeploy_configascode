# AutoDeploy configuration for a selected AAP

The current production controller retains its older four deployment templates
and their history. Future configuration bundles exclude those four, the older
destroy template, their workflow, the original provisioning inventory and its
Machine key. This changes what future installations receive; it neither deletes
production objects nor changes the four shared playbook files. The newer
four-stage templates remain the deployment implementation. The separate
use-case prerequisite template remains because selected setup still uses it.

## Source and destination access

An installed AutoDeploy source API credential uses the receiving AAP's verified
API URL and selected token. It does not retain the original controller's URL or
bearer. Its saved stage targets start empty so another run cannot silently reuse
the instance selected during capture. Registry, repository and Machine access
still use their existing credentials.

The selected-use-case launcher uses the existing injected source API credential
and endpoint-specific CA, verifies that this source owns the running job, then
launches the reviewed prerequisite/import templates. The destination comes from
the existing instance-indexed token store and inventory metadata. Installing
onto the launching AAP or another selected AAP uses the same importer; source
and destination API credentials remain separate. The launcher creates no
temporary source token and reads no installer password.

The source's shared and recovery inventories remain mandatory. A Hactar project
inventory alias is optional when that project is not installed on the receiving
AAP: only a genuinely empty inventory read together with verified administrator
visibility permits skipping that API alias. Every present alias retains its
identity checks, and the canonical encrypted Hactar policy copy is still updated.

## Installation access before the vendor installer

After Stage 01 authenticates the newly created guest, reads its native libvirt
ownership and publishes its consumed reservation, it preflights the existing
source job and three maintained encrypted policy captures. It then adds only:

1. Public IPv4 HTTPS for that exact guest bridge, address and MAC, retaining the
   protected/private destination exclusions.
2. TCP 443 from that guest to its own pinned hypervisor's public address, so its
   future AAP can use its own trusted public API.

The existing isolation helper validates the complete old policy and actual VM
ownership, checks nft syntax, applies atomically and verifies native firewalld
and persisted state. The existing publication action saves policy and placement
in the existing encrypted captures and source inventory. The selected reservation
is rechecked before and after source synchronization. No API token is created by
this step. Other guests, production exclusions and previously released clients
are preserved. Stage 04 can subsequently add the exact managed SSH port.

The current local-policy schema represents destination/port cross products. If
separate management and public addresses would unintentionally grant additional
pairs, reconciliation stops for review rather than broadening access.

An unpublished failed permission is restored using the exact prior native rule
states. Once encrypted publication succeeds, a failed source synchronization
retains that approved live state for an idempotent retry.

For an existing registered AAP, the existing base configuration template accepts
only `--tags aap_installation_access` as a bounded repair operation. This resolves
its saved route and SSH trust, reconciles those same permissions and removes its
temporary trust file. It does not allocate a name, create/restart a VM, install
AAP, apply a subscription, rotate a token or run the ordinary base dispatcher.

The same publication saves the current operation's exact native rule in
`firewall_additional_zone_rules`, which Hactar's base firewall playbook consumes.
It preserves prior declarations, adds the selected pair idempotently and refuses
conflicting or duplicate declarations for that pair. Updating only the live
firewall and the isolation-policy aliases would leave a fresh rebuild incomplete.
The base template must have tag prompting enabled so AAP accepts the requested
tag instead of ignoring it. Check the launch metadata first and verify the launch
accepted `job_tags: aap_installation_access`; no ignored tag is a valid repair run.

## Inventory names and lifecycle ownership

The inventory display name follows `aapNN-vNN`. The existing physical libvirt
name, allocation record and token-store key remain unchanged. The existing
`vm_resource.vm_name` identifies that physical owner; no separate alias map is
created. Registered-stage inventories without an AAP host entry continue to
accept the physical registry key directly.

New verified inventory registrations use the display format. Callbacks preserve
an existing display label and its placement-group membership instead of
recreating the former name. Token publication and retirement use the route's
physical name. Decommissioning resolves and verifies the same physical owner
before removing its actual inventory label and group membership.

The imported shared inventory contains selected AAP/hypervisor placement and
preserves existing members. Full lifecycle cleanup additionally needs verified
ownership for related guests and every surviving policy permission. Those facts
must be registered by the relevant VM/service deployments; copying unrelated
production hosts or assuming a missing record means deletion is not permitted.

## Future extraction scope

The encrypted extraction scope explicitly lists the retained production-only
objects under `source_exclusions`, by resource kind and exact name. Project and
label discovery therefore cannot add them back to future bundles. Excluded
source objects remain untouched. A retained job or workflow still referencing
an excluded object stops extraction for review. Remove the obsolete portable
inventory/key aliases and old code-owned workflow adapter together with the
future-bundle definitions.

Keep shared-inventory extraction reference-only, with explicitly reviewed
members. Source-specific scope pins and three-way baselines still require
review before an extractor is used on another controller; installation of its
template does not prove that its runtime scope is portable.

Configuration import success proves installed objects and relationships. A new
VM, installation cycle, complete decommission and independent version-to-version
recovery remain separate live acceptance checks. See the
[agreed recovery and use-case targets](recovery-and-use-case-targets.md).
