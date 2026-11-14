# Prepare AIOps settings during its existing CaC import

The existing **Deploy AIOps Selfhealing Demo CaC** template still calls the
single `deploy-cac-project.yml` playbook. Its existing private repository token,
CaC/runtime Vault credentials and selected target API authentication are reused.
There is no separate preparation job or application workflow.

## Before the configuration roles create resources

The capture's ready flag, its declared review checks and the effective import
variables must allow deployment before any data commit or target lookup. An
operator hold remains a hold; preparing settings cannot bypass it.

The importer binds the selected inventory entry's `vm_resource.vm_name` and
allocation number to its authenticated HTTPS API. The selected hypervisor's
existing connection pin and the AAP VM ownership must agree. New public names
use the allocation's `aap27.vNN`, `redhat.vNN` and `zabbix.vNN` forms. An already
recorded deployment retains its actual pre-migration URL.
Controller's canonical positive decimal counter text is normalized by the same
inventory identity helper used elsewhere. Boolean, floating-point, padded and
otherwise malformed values are refused.

The existing encrypted AIOps capture explicitly names the native Machine
credential supplied by target base configuration. Preparation verifies that
exact credential through the target API; it creates no credential type or
replacement credential. It creates the selected private instance mapping with
that reference, monitoring off, and one strong Event Stream Basic password.
That password is persisted before the ordinary configuration roles use it.
Retries retain the accepted password, including a lost Git push acknowledgement.
Existing deployments' known runtime/password material is preserved rather than
rotated or copied into another allocation.

The same pre-import phase reads the existing vaulted `vault_rhsm_org_id` and
`vault_rhsm_activation_key` already used for AAP's RHEL installation. It seeds
only this instance's `demo_mcp_subscription` in the existing runtime Vault,
with its physical instance key and the required RHEL 9 BaseOS/AppStream
repositories. Existing selected values must agree; a different organization or
activation key stops for review instead of replacing credentials. All other
runtime settings and instances are preserved. The protected input is passed
only to the existing preparation action, with `no_log`, before import; the
post-import phase receives no RHSM material. This creates no new credential,
store, job or registration activity. The existing MCP job later performs the
actual RHEL prerequisite configuration on its verified TRA.

Absent auxiliary guests remain absent. Only matching existing native source
inventory `vm_resource` records can populate a Linux guest entry. Their VM name,
number, hypervisor, UUID, disk, network, address, machine ID, SSH keys, account
and port must agree. Another allocation's identities or changed saved ownership
are refused. The helper does not create, discover or claim to verify a running
VM; the existing VM deployment jobs establish that evidence.
Zabbix retains its distinct schema 2 native clone provenance, saved-image hash,
authenticated API version, frontend/API references and native monitoring IDs.
Its disabled source inventory row contains metadata only, without a guest SSH
connection or guest machine ID. It is not converted into a generic Linux record.

## Native monitoring record publication

Each instance keeps its Zabbix VM definition at `aiops_instances[instance].zabbix`.
Its `configuration.firewall.guest_host_clients` contains that VM's explicit
permission, and `configuration.cac_import` identifies the existing target-local
importer, source inventory, placement group and actual AAP inventory alias.
The importer resolves these native IDs from the selected AAP; none is hardcoded.
The former sibling `instance.firewall` is moved into this one VM configuration,
with conflicting copies refused. Existing VM fields, other instances and secrets
remain intact. Before creation, the VM section can contain configuration only;
UUIDs, addresses and machine identity are never invented.

After the pinned hypervisor verifies the native domain and DHCP identity, the
existing Zabbix job configures the appliance through its private API from AAP.
It writes the authenticated `vm_resource` and API references to a disabled,
metadata-only row in the existing native source inventory. No SSH connection
into the appliance is used. Internet forwarding remains blocked before boot,
during reconfiguration and afterward.
The observed bridge gateway joins that same verified resource. It then launches
the existing AIOps CaC importer with its saved credentials. This pre-import phase
reads the newly available host variables, validates the complete VM record, and
derives only the fresh owner's own-bridge TCP 443 permission. A later explicit
permission removal is preserved rather than recreated on every import.

The same existing action publishes the encrypted capture/runtime pair through
its already approved token and concurrency checks. The existing target API
client retains its fixed-origin HTTPS and redirect guard during discovery.
No new Git publisher, credential type, task store, service or Job Template is
introduced. The parent waits without a firewall lock and reloads the newly
rendered inventory host and saved-template ciphertext before frontend and
permission application continue. This reloading is required because an already
running job retains its original inventory and Extra Variables.

The small validation functions remain in the existing settings module: native
Controller content supplies API operations, while these pure data checks enforce
the demo's cross-record VM identity and one-copy layout before encrypted writes.
Native collection modules do not implement this project-specific data model.
Tests exercise real local Git/Vault publication, native Ansible call sequences
with substituted Controller endpoints, collisions and importer failure. Those
fixtures do not prove a live fresh-instance deployment.

Upgrade the code, common-source pins and protected layout together. Before
running the updated policy readers, use the normal importer to move existing
firewall data into each Zabbix VM's `configuration` and render its importer
binding. Windows and Assistant consumers must use the matching updated common
source; an older common pin cannot read this layout. Keep deployment jobs
stopped during that coordinated migration, then verify the normal Zabbix job.

## After the existing roles create resources

Preparation reads the selected target's native website fault-template ID and
generated GitLab webhook key. The template must match its exact name, SCM
project and playbook. It also reads the native Event Stream UUID and requires
its HTTPS endpoint, organization and Basic credential to match that same AAP.
These are GET requests. Preparation does not generate a webhook key, mint a
different Event Stream identifier or activate a rulebook.
The native API may include the default HTTPS port explicitly. An already saved
equivalent URL is retained verbatim only when its exact selected hostname,
native UUID path and credentials still match.

The runtime Vault receives only those selected-instance readbacks. Existing
values must agree; an unexpected key/identifier change stops for review. The
capture's embedded runtime ciphertext is refreshed, then saved template
definitions are reapplied using the existing Controller configuration role.
All AAP resource writes remain with the existing configuration roles and
modules. Importing configuration launches no application or fault job.

## Encrypted persistence and concurrent writers

Both maintained AIOps Vault files are updated in the importer's existing private
checkout. The existing token has explicitly approved Contents read/write access
to that repository. Both files are committed together, preserving their separate
Vault secrets, original headers, unrelated instances and literal data. No secret
is placed in a Git URL, command argument, log or plaintext launch default.

A conflicting Git update causes a bounded reread and data merge against the
accepted remote commit. There is no force push or automatic secret rotation.
Accepted remote state is reread before any newly prepared password is used.
Write denial or an unavailable Vault key stops before configuration roles run.
The existing importer cleanup removes the private checkout on success/failure.
This state preparation requires a normal import; check mode does not persist
new secrets or claim a usable first deployment.

## Functional boundaries

This removes the first-import requirement for already-created auxiliary guests.
Testserver/TRA creation, Zabbix deployment, MCP target-side builds and application readiness still use their existing
deployment paths. Shared DNS/frontend/provider inputs must come from explicitly
approved sources. Instance URLs, native identifiers, ownership records and
target-local AAP/EDA credentials remain specific to the selected environment.

The controlled demo retains the approved Zabbix image's existing API credential,
as used by the earlier MCP setup. Its selected runtime namespace supplies that
value to the existing MCP-token field; the consumer still requires the selected
Zabbix resource and endpoint. A fresh-token producer or an encryption bridge is
not required for this baseline, and no token is claimed to have been newly minted.

The importer does not invent Vertex ADC, account or project settings. Prepare
provider inputs only from an operator-approved source for the selected demo;
storing a value does not itself authorize additional provider or model activity.

Core 2.20 requires explicit template trust for code-generated expressions. The
existing preparer marks only its generated importer binding, firewall-owner
projection and reviewed policy rewrite accordingly. These resolve to native
configuration before inventory publication. Credential text and unrelated
literal values are not granted template trust. The projection regression also
serializes and reloads the prepared capture through the existing preserving YAML
codec, verifying that native mappings and literal values survive publication.
Publication compares literal-template paths as well as values, so correcting a
previously literal projection is saved even when its text stays identical. An
encrypted Git regression verifies that upgrade without changing runtime
ciphertext or unrelated literal data.

Local tests use synthetic API responses and real local encrypted Git repositories,
including concurrent writers, lost acknowledgements, different Vault keys,
native Ansible rendering in both modes, refusal cases and literal preservation:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/aiops-settings-tests python3.12 -m unittest discover -s tests -p test_aiops_settings.py -v
```

Existing protected multi-project rendering fixtures also accept
`AAP_CAC_TEST_VAULT_PASSWORD_FILE` when an isolated checkout is outside the
usual workspace layout. The value names a local key file and is not committed.

A successful local fixture or CaC import is not evidence that a successor's VMs,
monitoring, private MCP or model-based remediation have been deployed.
