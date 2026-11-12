# Project AAP CaC execution environment v2

The current image is **ee-proj-aap-cac:2.0.0**. Use the
[automated build and verification playbook](../docs/execution-environment-build.md)
and [Orchestrator CaC hook](../docs/orchestrator-execution-environment.md).
The two direct requirements and every transitive wheel are pinned below this
directory; all nine additions now come from Red Hat Trusted Libraries.

The following describes the historical EE-v1 publication and its validation.
Its manual command examples identify that older artifact; they are not the
current v2 build procedure. The base inventory remains valid for both versions.

# AAP AutoDeploy EE-v1

This derived execution environment adds the Kubernetes Python client and the
JSON patch library required by the intended Orchestrator Kubernetes modules.
Its public base is the digest-pinned Red Hat AAP 2.7 minimal RHEL 9 image in
`Containerfile`. The verified base provides Ansible Core **2.20.10**, Python
**3.12.15**, user `root`, entrypoint `entrypoint` and command
`ansible-runner run /runner`. The recipe inherits those settings.

`requirements.txt` declares `kubernetes==35.0.0` and `jsonpatch==1.33`.
Their required transitive Python dependencies are part of this addition.
Client 35 declares Python 3.12 support and accepts the base's urllib3 2.8.0.
The intended `kubernetes.core` 6.4.0 modules require Kubernetes >=24.2.0,
PyYAML and jsonpatch; the base already supplies PyYAML. The Kubernetes package
does not itself depend on jsonpatch, so both direct requirements are necessary.

Ansible collections continue to come from native project
`collections/requirements.yml` files and the receiving organization's configured
authenticated Galaxy sources. This image does not bake collections or replace
Core, Runner, the operating system, the base entrypoint or the base command.
DNS validation continues to use the existing native tools; this build does not
add dnspython or reintroduce the retired lookup/delegation workaround.
The derived image is a separately maintained artifact; record its build and
validation evidence with its release.

The complete [base package inventory](base-inventory.json) records 57 Python
distributions and 240 RPMs. Beyond Core and Python, the base supplies Runner
2.4.3, WinRM 0.5.0, PSRP 0.9.1, Paramiko 5.1.0, NETCONF, Kerberos/NTLM/CredSSP,
HTTP/TLS and XML/YAML libraries. No third-party Ansible collections were found.

## Build and verify

Run these commands from the repository root using the existing Podman and Skopeo installations
and approved registry access. Inspect the exact local base digest first and
match its image ID against the protected base inventory receipt. If the image is
missing, obtain that exact digest through the existing authenticated Red Hat
registry route before building.

```bash
podman image inspect registry.redhat.io/ansible-automation-platform-27/ee-minimal-rhel9@sha256:aea45867ebbfcb57bba69b3b6e33542dbbe95f237dfdf35e8b68773b4f3268f8
podman build --pull=never --file execution-environment/Containerfile --tag localhost/aap-autodeploy-ee-v1:1.0.0 execution-environment
podman run --rm --pull=never --network=none --entrypoint /usr/bin/python3 localhost/aap-autodeploy-ee-v1:1.0.0 -m pip check
podman run --rm --pull=never --network=none --entrypoint /usr/bin/python3 localhost/aap-autodeploy-ee-v1:1.0.0 -c 'import importlib.metadata as m,json,sys,ansible,kubernetes,jsonpatch,requests_oauthlib; assert ansible.__version__ == "2.20.10"; assert sys.version_info[:3] == (3,12,15); assert m.version("kubernetes") == "35.0.0"; assert m.version("jsonpatch") == "1.33"; print(json.dumps({"core":ansible.__version__,"python":sys.version.split()[0],"kubernetes":m.version("kubernetes"),"jsonpatch":m.version("jsonpatch")}))'
podman image inspect --format '{{json .Config.User}} {{json .Config.Entrypoint}} {{json .Config.Cmd}}' localhost/aap-autodeploy-ee-v1:1.0.0
```

`requirements.lock` pins all nine new distributions and their wheel SHA-256
hashes, resolved inside this exact base without replacing any of its 57 Python
distributions. The Containerfile enforces that lock with `--require-hashes`.
When updating the base or direct requirements, resolve the complete additions
again inside the new base and retain the resolver report before rebuilding.
An exact base digest and direct pins alone do not freeze transitive resolution.
Compare the final Python package and RPM inventory against the protected base
inventory. Account for every package change, and verify the inherited image
configuration and Core/Python versions. Keep build logs and receipts protected;
do not put registry authentication material in the build context or image.

The checks above establish versions, dependency consistency and Python import
availability with networking disabled. They do not establish Kubernetes API
authentication, cluster connectivity or successful Orchestrator deployment.
Those require their separately authorized functional checks using the runtime
collections and protected cluster inputs.

## Publish to the existing private automation hub

Use the existing private Hub registry and an existing account authorized to
create and push the selected container repository. AAP 2.7 registry login uses
that account's username and login password; a controller API bearer token is not
the registry password. Preserve normal TLS and certificate verification.

This Bash example uses a temporary authentication file and prompts without
putting the password in command arguments or shell history. Replace only the
generic registry placeholder with the protected selected Hub location.

```bash
ee_registry=hub.example.invalid
ee_authfile=$(mktemp)
chmod 600 "$ee_authfile"
printf '{}\n' > "$ee_authfile"
trap 'rm -f "$ee_authfile"' EXIT
read -r -p 'Hub username: ' ee_registry_user
read -r -s -p 'Hub password: ' ee_registry_password
printf '\n'
printf '%s' "$ee_registry_password" | podman login --authfile "$ee_authfile" --tls-verify=true --username "$ee_registry_user" --password-stdin "$ee_registry"
unset ee_registry_password
ee_export=$(mktemp -d)
skopeo copy --retry-times 0 --dest-compress --dest-compress-format gzip --dest-compress-level 1 --dest-force-compress-format containers-storage:localhost/aap-autodeploy-ee-v1:1.0.0 "dir:$ee_export"
skopeo copy --retry-times 0 --preserve-digests --dest-authfile "$ee_authfile" --dest-tls-verify=true --digestfile "$ee_export/published-digest.txt" "dir:$ee_export" "docker://$ee_registry/aap-autodeploy-ee-v1:1.0.1"
ee_digest=$(cat "$ee_export/published-digest.txt")
ee_download=$(mktemp -d)
skopeo copy --retry-times 0 --preserve-digests --src-authfile "$ee_authfile" --src-tls-verify=true "docker://$ee_registry/aap-autodeploy-ee-v1@$ee_digest" "dir:$ee_download"
```

Verify the repository tag and registry manifest digest after the push. Record
the published digest independently from the local image ID: they identify
different objects. AAP's existing native Container Registry credential must
permit pulling the private Hub image before any job can start with it.
Set the named `AAP AutoDeploy EE-v1` definition, desired default and intended
project/template references through the existing AAP and CaC paths after the
published artifact passes verification. Retain explicit template bindings when
evaluating which jobs inherit a changed default.

## Primary references

- [Kubernetes 35.0.0 package metadata](https://pypi.org/pypi/kubernetes/35.0.0/json)
- [kubernetes.core 6.4.0 Python requirements](https://raw.githubusercontent.com/ansible-collections/kubernetes.core/6.4.0/requirements.txt)
- [AAP 2.7 image publication and pull workflow](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/administer-proc_obtain_images)

## Verified build checkpoint

The initial image built successfully with Core 2.20.10 and Python 3.12.15.
Offline imports and `pip check` passed; all 57 original Python distribution
versions and the complete base layer chain were preserved. The inherited user,
entrypoint, command and working directory matched the Red Hat base. The local
image ID is `4715ff8f1ff18ffa090dc0dc7a9529a277f7c0550bbca4e1c012b69d67a5205a`.
Offline Kubernetes object/date serialization and a JSON patch operation also
passed without cluster access. The initial `1.0.0` publication was rejected by
AAP's native image pull: Hub stored a truncated compressed base layer. An earlier
local pull could reuse cached layers, so its matching image ID did not establish
remote blob integrity. The failed native job remains recorded.

The replacement `1.0.1` publication preserves the image configuration and every
uncompressed layer. Native Skopeo gzip level 1 compression gives fresh layer
digests, allowing a normal upload without changing Hub access policy or storage
internals. Download the immutable manifest to a new directory transport with no
local image cache and check every layer's size and SHA-256 before testing normal
AAP execution. Keep TLS and digest verification enabled.

Replacement manifest
`sha256:07b695ce8df1dc31403aac805ad00ab4767c46a8c67a70484fecb231cccca217`
passed a fresh directory-transport download: all three compressed layer sizes
and SHA-256 hashes, every decompressed layer digest, and the original image
configuration were verified. Normal AAP job `3729` then passed in 99.483 seconds
with an actual Core 2.20.10 runtime header. Source AAP's global default, all
62 managed templates and the Hactar project default now select EE-v1; the
original official EE and upstream registry credential remain available. The
candidate used `always` for its initial native pull proof and then returned to
`missing` with the immutable image pin. Fresh-receiver acceptance remains
separate because its network policy must permit the selected registry.

## Persist upload timeouts in deployment and CaC

The initial Hub upload failed while its API workers hashed a large layer:
workers had a 10-second limit and the native registry route an effective
15-second request/idle limit. This was a timeout diagnosis; no OOM evidence was
found. With the owner's approval, only the Hub API container was reconciled to
200 seconds using its existing native module and image, and only the registry
route was changed to 600 seconds. Other running containers retained their starts.
The retry accepted the manifest, but subsequent native AAP verification exposed
a truncated stored blob left from the earlier upload. A successful push alone
is therefore insufficient evidence of a usable image.

`vars/main.yml` declares `aap_hub_gunicorn_timeout: 200` and
`aap_registry_route_timeout: 600`. Stage 03 writes the supported worker setting
to installer inventory before installation. Stage 04 discovers this receiver's
native `/v2/` Hub route, preserves its routing/authentication/TLS policy, applies
the two timeouts through `ansible.platform.route` and verifies readback. It uses
target-local IDs and skips mutation when the detail response already matches.
The global platform timeout and unrelated routes remain unchanged.

Three real-Ansible fixtures passed in the actual stock Core 2.20.10 EE with
`ansible.platform` 2.7.20260930: installer replacement/rerun, native route
update/idempotency and seven refusal scenarios. Both complete playbook syntax
checks passed. This verifies future deployment behavior without rerunning the
completed installer.

## Retire a failed owned publication

After its replacement passes uncached integrity and normal AAP execution, use
Hub's supported repository `remove_image` action for the exact failed manifest.
Check the owning repository, tags, signatures and manifest-list references
before submission, record the returned native task and follow it to completion.
Verify that the replacement and shared content remain in the latest repository
version. Do not assume a registry DELETE endpoint exists, bypass an unsupported
repair policy, edit storage or use global orphan cleanup for a single image.

The initial failed `1.0.0` manifest is now absent from the current owned
repository. The healthy `1.0.1` image and shared configuration/layers were
preserved, and physical artifact files remained unchanged.
