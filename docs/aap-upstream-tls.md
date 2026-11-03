# Verified TLS for new AAP instances

New deployments verify both the public HTTPS endpoint and the nginx-to-Gateway
connection. The public certificate alone does not verify the upstream guest.

Stage 02 obtains the public certificate and publishes a temporary HTTPS frontend
returning 503. It has no unverified upstream while the new installer is running.
The existing public HTTP challenge and certificate prerequisites remain separate.

After installation, Stage 03 checks Gateway using the installer-managed CA at
`/home/<installer-user>/aap/tls/extracted/pem/directory-hash/ca-bundle.crt`.
The guest resolves its own platform hostname locally, as configured before the
installer runs. Certificate validation is enabled for this health check.

The public CA bundle is then read through the existing authenticated guest SSH
connection, with both guest and hypervisor host keys pinned. After checking the
selected hypervisor's machine identity, the job installs the bundle under
`/etc/nginx/aap-upstreams/<instance>.pem`. It verifies TLS to the guest's private
address using the platform DNS name as the expected certificate identity. This
probe sends no application credentials and changes no system trust store.

The delegated SSH address, user and port read
`hostvars[inventory_hostname].aap_instance_route` explicitly. That route belongs
to the original guest inventory entry. Ansible otherwise looks for connection
variables on the delegated hypervisor, where this guest-specific route is absent.

The final nginx frontend enables upstream certificate verification, the
instance-specific CA bundle, SNI and explicit hostname verification. The full
nginx configuration must validate before reload. Publication failure restores
the prior instance configuration and checks it before reloading. Successful
publication is followed by a certificate-verified public API health check.

When installation has already succeeded and only proxy publication failed, run
Stage 03 with the Ansible tag `aap_upstream_tls`. The initial registered-instance
selection and SSH trust tasks carry `always`; the tag then runs installed Gateway
CA verification, authority publication and public verification. It excludes all
preparation, installation and async-observer tasks. Confirm the original installer
returned zero before using this retry; an expired or cleaned async result is not
a reason to repeat installation. An ordinary untagged launch keeps the complete
installation behavior.

For a failed hypervisor identity command, the temporary variable
`aap_proxy_identity_diagnostics: true` exposes that command's native result. Its
only command is `cat /etc/machine-id`; it has no secret arguments. Other secret
tasks remain protected, and this option defaults to false. Remove the diagnostic
variable and restore the Job Template's usual verbosity and tags after checking
the outcome.

Infrastructure SSH here installs nginx trust; use-case API tasks continue to
use public HTTPS. This adds no API delegation, execution node or credential
selection mechanism. Existing deployments and production SSL were not changed
when this code was implemented. No deployment jobs were launched for validation.

Focused validation uses real local TLS peers to test correct and incorrect
authorities, hostname mismatch, missing trust and unchanged global trust.
Actual Ansible template/copy tasks cover publication and rollback; both
templating modes pass. Both rendered nginx states also pass the installed nginx
binary's syntax check with temporary in-memory certificates and configurations,
without installation or reload. A new end-to-end VM deployment remains separate.
