# Instance API and MCP tokens

Operators launch the project's existing Deploy … CaC Job Template and choose
`aap_instance_key`. The inventory entry supplies `ansible_fqdn`; the saved
**AAP API/MCP Auth Token Store** supplies that instance's bearer token. The CoP
roles receive that URL/token with TLS verification enabled. The importer does
not use SSH, installer-password discovery, an extra job or a wrapper playbook.

**Pseudo Instance Key Store** is the credential type, meaning its schema and
injector. It defines one secret multiline field, `instance_tokens`. The actual
credential contains a populated JSON document:

```json
{"schema_version":1,"instances":{"test-instance":{"hostname":"https://aap27.v07.example.invalid","token":"EXAMPLE_ONLY","token_id":1,"expires":null}}}
```

AAP writes the injected data to a private job file. `AAP_INSTANCE_KEY_STORE_FILE`
contains its filename. Selection refuses unknown instances, expired or invalid
records, inventory/FQDN mismatches and additional native AAP credential injectors
that could override authentication. Secret data stays protected during debugging.
Each project keeps its separate private Git reader and CaC Vault credential.

## Who fills it

Base creates or reuses its original persistent administrator MCP token; this
same token supports remote API calls. Its protected target-side recovery file
remains unchanged. With `aap_instance_key_store.publish: true`, base verifies the
bearer, saves the selected record under `aap_instance_api_credentials` in the
canonical encrypted AutoDeploy capture, and updates the populated credential on
the **source AAP running the deployment**. Merely defining a credential type does
not fetch values from a Vault; the publishing action performs those steps.

The source needs the approved type installed, its existing source API credential
and CA, the repository writer, environment Vault and the existing CaC Vault.
The writer replaces that stage's repository reader because both share a Git
credential type. No new source token or target token is minted for publication.
The source API is bound to the current running job, template and SCM revision.
Git updates use normal compare-and-swap pushes, preserve other records and
`!unsafe` templates, and reread concurrent updates before source synchronization.
Failures keep the saved target token so a rerun can repair publication.

Separate native API credentials may be retained for manual uses. They are not
attached to the generic deployment templates; set an explicit Request Timeout
when creating them through the API.

## Temporary limitation and verification

Every job receiving this credential can access every token stored in it. The
per-instance selector prevents mistakes; it does not provide isolation between
untrusted job code. This temporary design is owner-approved because no external
secret manager is available. `bead-wd-72f.13` tracks replacement by an enterprise
secret manager; that future choice is separate work.

Tests exercise selection, mismatches, masked API inputs, real encrypted Git
updates, source-save failure/retry, concurrent-map retention and reuse of the
same persistent token. A complete fresh deployment is a separate live proof;
offline tests alone do not establish that it finished.

## Selected private MCP connection

An existing instance record may additionally contain `mcp`, holding its private
HTTPS endpoint and installed public `ca_pem`. The credential type, JSON schema
version, original token/ID/expiry and ordinary CoP API authentication remain
unchanged. Legacy records without this metadata still authenticate normally.
Base reads and verifies the authority through its existing authenticated guest
bootstrap path, then publishes it only for that selected instance; a conflicting
saved endpoint/CA stops for review. No new token is created.

The default file is the installer's `tls/ca.cert`, not the extracted system-root
bundle. Only this instance's relevant public issuer/chain belongs in the encrypted
runtime. Copying unrelated public roots expands Vault ciphertext enough to exceed
ordinary proxy request limits. Public provider HTTPS retains normal system/vendor
trust; the selected private issuer is additive application trust only.

Publish compatible readers before backfilling. Run existing base configuration
for the selected instance, refresh AutoDeploy CaC on the receiving AAP, then
refresh AIOps CaC. The existing AIOps preparation copies only selected token/CA
into its existing encrypted runtime; it performs no SSH. The normal AIOps
Claude/MCP installer uses private MCP and application-only CA trust. Other
namespaces and provider credentials are preserved.

Current importers share the AutoDeploy main project with update-on-launch and
zero cache timeout. Their normal project sync must load compatible readers
before accepting new metadata. Older ordinary selectors reject the extra field,
and older ordinary publishers could discard it. Existing pinned guest
release/retire/network operations use separate capture paths that preserve the
complete token mapping; this change requires no unrelated guest lifecycle pin
change. Receiving stores are refreshed by their existing AutoDeploy CaC import,
not assumed to change when source base publication finishes.
