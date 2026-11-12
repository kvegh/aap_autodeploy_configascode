# Receiver-owned Orchestrator execution environment

Deploying the `automation-orchestrator` CaC project now runs the shared
`tasks/build-execution-environment.yml` before rendering or importing its
execution-environment definitions. The selected receiver builds and publishes
`ee-proj-aap-cac:2.0.0` to its own Automation Hub. The build verifies the remote
manifest, blobs, image configuration and runtime before returning a digest-bound
image. An existing version with different build inputs is rejected.

Only the reviewed `Orchestrator EE` definition receives that verified image.
Its name, organization, description, pull policy and native registry credential
are preserved. Other EE definitions are preserved. A build failure stops the
import before ordinary configuration roles run. Other CaC project imports do
not invoke this hook. The API continues using the selected target's bearer;
registry passwords do not replace `aap_username` or `aap_password`.

Every reviewed project import also resolves the receiver's existing native EE
named `ee-proj-aap-cac` before resource normalization. It reads that object's
immutable image and associated `Project AAP CaC EE registry` credential from the
selected receiver, requires the image and credential to use that receiver's own
Hub with TLS verification, then sets `aap_shared_execution_image`. Reviewed
capture image fields explicitly reference `{{ aap_shared_execution_image }}`;
the importer never searches and replaces other images. The separate AutoDeploy
restoration path resolves the same binding before its EE configuration role.
Missing native configuration stops import. Orchestrator additionally requires
the native EE image to equal its independently verified build result.

## Protected prerequisites

The existing encrypted Orchestrator capture supplies
`orchestrator_registry_username` and `orchestrator_registry_password` for the
digest-pinned Red Hat base. It also needs an explicitly provisioned
`orchestrator_ee_build_targets` map, keyed by the target's immutable registered
instance name. Each record has exactly these fields:

| Field | Value |
| --- | --- |
| `hostname` | The exact selected target API HTTPS origin. |
| `route` | Its existing verified `aap_instance_route` handoff, including the pinned hypervisor and guest public SSH keys. |
| `machine_id` | The receiver's authenticated current machine ID. |
| `ssh_username`, `ssh_password` | Its existing primary SSH login with the already approved sudo access. |
| `build_user` | Its existing nonroot AAP installation account, reached through that approved sudo access. |
| `hub_username`, `hub_password` | Its own existing Hub registry login. |

Keep the entire map encrypted with the project's existing Vault credential.
Do not copy another receiver's Hub password or infer a registry password from
a Controller API bearer or masked credential response. Missing records stop
the deployment; there is no Source Hub or direct-IP fallback.

The importer job must have the existing hypervisor Machine credential attached
so its strict public-key ProxyCommand can authenticate. The selected inventory
entry must provide `ansible_host`, `ansible_fqdn` and verified `host_keys`.
The normal `aap_inventory_instance_name` rules resolve inventory aliases. Both
the route and an authenticated machine-ID read must match before building.
Temporary SSH trust is removed on success and failure.

The receiver must already have the native Container Registry credential named
`Project AAP CaC EE registry`, bound to its own Hub and the selected login,
with TLS verification enabled. The hook checks that public binding without
reading or replacing the masked password. Ordinary base configuration owns
that credential and the platform default EE.

The machine-identity read uses the primary SSH login without escalation. The
hook then uses the existing sudo access to read the installation account's UID,
requires a positive nonroot UID, and runs the shared builder as that account
with its actual `/run/user/UID` runtime directory. It requires native `podman`
and `skopeo` and existing outbound access
to the approved base and package sources. It installs no host tools, changes no
network policy and creates no extra job template or persistent digest store.
This deployment is intentionally unavailable in check mode because verification
requires the real native build and publication.

## Focused verification

Run `python -m unittest discover -s tests -p test_cac_orchestrator_ee.py -v` with
the existing Ansible test interpreter. The native Ansible harness replaces only
external API, SSH-read and build actions with synthetic boundaries. It checks
strict delegation and cleanup, rejects a different target, Hub binding, machine
or unverified/foreign image, and verifies that unrelated EE data and bearer-only
API authentication remain unchanged. It does not claim live build acceptance.
`tests/test_cac_shared_execution_image.py` additionally exercises real capture
normalization with the resolved binding and rejects missing, foreign or mutable
images, incorrect registry bindings, disabled TLS and Orchestrator build/native
image disagreement before import.
