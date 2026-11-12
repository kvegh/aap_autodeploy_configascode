# Build ee-proj-aap-cac in the receiving AAP

`build-execution-environment.yml` builds and publishes the versioned project EE
using the receiving installation's own private automation hub. The default
repository and AAP execution-environment name are **ee-proj-aap-cac**; the
default image tag is **2.0.0**. Existing earlier EE definitions remain separate.

The reusable implementation is `tasks/build-execution-environment.yml`. It can
also be included by the existing AAP configuration flow with task delegation.
It preserves the caller's inventory connection, build user and become settings.
The source assets come from the current project checkout; the build context and
registry authentication file live in a private temporary directory on the
actual build host.

## Required inputs and prerequisites

The build host must already provide working **Podman** and **Skopeo** for its
selected user. The playbook checks their presence and does not install tools,
enable repositories or change operating-system packages. That user needs access
to native container storage and permission to publish the selected repository
in the receiving Hub. Keep one publisher active for this versioned tag.

Normal fresh AAP deployment declares the receiving VM's `skopeo` prerequisite
in `03-aap-install.yml`, alongside its existing `ansible-core` installation and
after its existing subscription/repository setup. This uses native DNF and the
subscribed RHEL repositories, with normal repository and TLS/GPG verification.
It does not enable EPEL or an OpenStack repository or install a pip substitute.
The existing containerized installer supplies Podman. A VM installed before this
prerequisite was declared needs the separately approved, narrow native `skopeo`
package installation before its receiver-local EE build.

Supply environment values through the existing protected inventory, Ansible
Vault or AAP credential injection. Do not commit filled plaintext examples.

| Variable | Meaning |
|---|---|
| `aap_ee_registry` | Required receiving Hub registry hostname, optionally followed by a port. Use a hostname such as `hub.example.invalid`; omit URL schemes, paths and user information. An explicit port must be 1–65535. |
| `aap_ee_registry_username` | Required existing Hub account with permission to push this repository. |
| `aap_ee_registry_password` | Required protected login password for that account. |
| `aap_ee_redhat_username` | Optional existing Red Hat registry login. Supply together with its password. |
| `aap_ee_redhat_password` | Optional protected Red Hat registry password. |
| `aap_ee_image_name` | Optional repository override; default `ee-proj-aap-cac`. |
| `aap_ee_image_tag` | Optional version override; default `2.0.0`. Choose a new version when changing recipe inputs. |
| `aap_ee_build_hosts` | Optional standalone play target; default inventory group `aap_ee_build`. |

When the official base is absent locally, Podman obtains its exact digest using
the supplied Red Hat pair or that build user's existing native registry login.
The Hub password is passed to native `podman login` through standard input,
with a mode-0600 temporary authentication file. Authentication material stays
outside the image build context and image. The entire owned workspace is
mode 0700 and is removed in `always`, including after failure. Registry commands
retain normal TLS and certificate verification.

The receiving Hub, its DNS/TLS endpoint and the existing registry route must
already be available. A build needs access to the official Red Hat registry
when the pinned base is not cached, and to the Red Hat Trusted Libraries index
for Python wheels. It does not contact the earlier Source Hub to obtain an
existing custom EE.

## Standalone invocation

Use the existing protected inventory and Vault password source. For example,
with generic paths:

```bash
ansible-playbook -i /secure/build-inventory.yml build-execution-environment.yml \
  --extra-vars @/secure/ee-build.vault.yml \
  --vault-id cac@/secure/vault-password
```

The inventory supplies the actual build host, user and connection policy.
The standalone play runs its selected hosts serially. This does not coordinate
two separately launched playbooks; retain the existing single-writer execution
rule. The implementation checks the tag again immediately before publication,
but a registry tag update is not an atomic compare-and-swap operation.

Ordinary AAP integration includes the same task file and consumes its verified
result. This standalone play does not create a Job Template, change AAP defaults
or launch an Orchestrator deployment.

## Public recipe and Red Hat provenance

`execution-environment/Containerfile` pins the official AAP 2.7 minimal RHEL 9
base by manifest digest. Its public `base-inventory.json` records the verified
image identity, Core **2.20.10**, Python **3.12.15** and 57 Python distributions.
The build verifies the local base against that recorded image identity.

The only direct additions in `requirements.txt` are:

```text
kubernetes==35.0.0
jsonpatch==1.33
```

`requirements.lock` pins all nine added direct/transitive distributions and
their approved Red Hat wheel SHA256 values. The Containerfile uses pip's
isolated mode, the **Red Hat Trusted Libraries** index, binary wheels and
`--require-hashes`. It does not configure a PyPI fallback. The lock's provenance
checks cover Red Hat package metadata and the selected wheel bytes; changing
versions or hashes requires a reviewed recipe change.

The nine additions are Kubernetes, jsonpatch, jsonpointer, durationpy, oauthlib,
python-dateutil, requests-oauthlib, tzdata and websocket-client. Existing vendor
Python distributions must retain their versions. The recipe installs no Ansible
collections: collections remain native project `collections/requirements.yml`
dependencies served through the receiving organization's configured sources.

Red Hat distribution provenance does not by itself certify this derived EE or
establish functional acceptance of the Orchestrator collection against a live
cluster. Keep the vendor base, derived artifact and live application evidence
distinct. Client import availability is verified here; cluster authentication,
API permissions and application deployment need their separately authorized
functional checks.

## Verification and publication

Before publishing a new artifact, the implementation checks:

1. The digest-pinned base identity and the candidate's inherited user,
   entrypoint, command, environment, working directory and original layer prefix.
2. `pip check` and offline imports with container networking disabled.
3. Exact Core, Python, Kubernetes and jsonpatch versions, a local JSON-patch
   operation and Kubernetes client construction without an API connection.
4. All 57 vendor distribution versions and the exact nine locked additions,
   with no unplanned Python packages.

Skopeo then exports the candidate to a new directory using gzip compression
level 1. This prepares the transport bytes before digest preservation: the
subsequent native push preserves that prepared manifest and its blob digests.
The implementation verifies the published tag's digest and recipe fingerprint.

Every successful run downloads the **immutable registry digest** into a second
fresh directory through Skopeo. It does not use a Podman image-store cache for
that download. Native Ansible `stat` independently verifies the manifest SHA256
and every referenced configuration/layer file's SHA256 and size. The verified
configuration must preserve the base behavior and layer prefix. The downloaded
image is loaded into native storage for repeated offline dependency, runtime and
package-inventory checks.

This distinguishes a healthy fresh registry read from a successful cache hit.
Digest checks, TLS verification and native storage validation stay enabled.
The gzip level changes transport encoding without changing the intended
installed filesystem or package set.

## Repeat behavior and result

The derived image carries a SHA256 fingerprint of the four public recipe
assets: Containerfile, direct requirements, hash-locked requirements and base
inventory. A matching local image can avoid a rebuild. A matching published tag
can avoid both build and push, but still undergoes the fresh registry and
offline verification above. An existing tag with a different fingerprint is
refused rather than overwritten. Choose a new tag after a recipe change.

This is artifact idempotency. Temporary directories, authentication and image
verification may still produce changes in an Ansible recap. Independent builds
also need not produce byte-identical manifests solely because their package
inputs match; consume the verified published digest returned by this run.

On success, `aap_ee_build_result` contains:

| Field | Meaning |
|---|---|
| `image` | Receiving-registry image reference using `@sha256:…`. |
| `tag` | Fully qualified versioned tag. |
| `configid` | Verified image configuration digest. |
| `fingerprint` | Public build-input fingerprint. |
| `verified` | `true` only after the complete verification sequence. |

The result is cleared before a new attempt. Failures expose only a safe public
task-stage name, not credentials or raw command results, and trigger workspace
cleanup. AAP/CaC integration must use the returned immutable receiving-registry
reference. It must not copy a prior installation's registry hostname, image
database ID or manifest identity into a new installation.

## References

- [Red Hat Trusted Libraries Python index](https://packages.redhat.com/trusted-libraries/python/)
- [Kubernetes client package metadata](https://pypi.org/pypi/kubernetes/35.0.0/json)
- [kubernetes.core 6.4.0 Python requirements](https://raw.githubusercontent.com/ansible-collections/kubernetes.core/6.4.0/requirements.txt)
- [AAP 2.7 registry publication and pull workflow](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/administer-proc_obtain_images)
