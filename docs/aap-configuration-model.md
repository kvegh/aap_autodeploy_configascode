# AAP configuration models and export coverage

Research checked on 2026-11-14. This describes available models and the limits of
the current integration; it does not establish complete scanner coverage or a
successful configuration round trip.

## Where the definitions come from

No single, complete, versioned, portable desired-configuration model for every
AAP component was verified. The usable definitions have several owners:

| Configuration | Authoritative starting point | What still needs checking |
| --- | --- | --- |
| Platform gateway | Its deployed OpenAPI schema and settings API | Relationships, write-only inputs, defaults and deployment-managed values |
| Automation controller | Its deployed resource APIs and endpoint metadata, plus collection module arguments | Exported object fields, associations, named references and import support |
| Event-Driven Ansible | Its own deployed OpenAPI schema | Credentials, activation references, event streams, RBAC and masked values |
| Private automation hub | Galaxy APIs and the deployed Pulp OpenAPI schema | Which resources describe reproducible configuration rather than content or task state |
| Intelligent Assistant | The installer or Operator configuration for the installed version, together with any relevant service APIs | Provider and MCP inputs, protected credentials, deployment settings and actual readable state |
| Dashboard and Analytics | Their deployment configuration and the relevant platform or service settings | Integrated versus standalone deployment, metrics configuration, external services and persisted preferences |
| Installation | Installer inventory or Operator custom-resource definitions | Inputs and secrets that are not readable through a component API |

An API schema describes requests and responses. It does not by itself describe
Git ownership, import order, portable references, creation-time secret capture,
or which values are safe to replay. A database backup is a different recovery
mechanism and is not a portable CaC model.

In AAP 2.7, use the platform gateway origin for component API requests. The
[documented API routing changes][routing] do not permit authenticating directly
against backend component hosts as an alternative.

## Observed schema coverage

Bounded, authenticated, read-only discovery against one existing installation
returned these schemas through its gateway:

| Schema endpoint | Observed paths | Observed component schemas |
| --- | ---: | ---: |
| `/api/gateway/v1/docs/schema/?format=json` | 126 | 121 |
| `/api/eda/v1/openapi.json` | 84 | 116 |
| `/api/galaxy/pulp/api/v3/docs/api.json` | 607 | 440 |

These counts identify that observation, not a product-wide guarantee. The
gateway document contained gateway paths; it did not include the Controller,
EDA and Hub models simply because the gateway routes their requests. Keep the
component schemas separate and record the installed versions when assessing
coverage. A complete Controller schema was not verified in this assessment.
The [gateway documentation][gateway-schema] explains its schema endpoint, and
the [EDA server documentation][eda-schema] documents EDA's own schema.

## What the CoP exporter promises

The CoP [`filetree_create` capture guide][capture] describes exporting the
Controller, Gateway, EDA and Hub objects supported by the collection. Its
[`filetree_create` README][export-role] includes an export-everything example,
but defines the `all` selection as invoking all of the role's supported exports.
No guarantee of every AAP field, relationship and component was verified.

The role already documents schedules, notification associations, inline approval
nodes, instance groups, RBAC options and settings. Several unsupported Controller
features in this project's current extractor are therefore integration gaps;
they are not established omissions from CoP. This does not make CoP a superset
of this project's scanner. Compare the actual capabilities of both implementations
before choosing what to reuse.

The role's documented settings overrides also show why an export needs review:
some omitted or empty settings require explicit preservation. API-hidden
credential values become variable references or masks, not recovered passwords.
The capture guide separately lists remaining limitations in selectors, output
and default filtering. Dedicated Intelligent Assistant, Dashboard or Analytics
export types were not found in the inspected export selection list. This does
not prove that every setting associated with those features is absent: some
settings can be represented through a general settings export.

The [CoP conversion guide][conversion] documents component deployment order and
the separation between `infra.aap_configuration` configuration roles and the
extended collection's export and comparison helpers.

## Applying this to extraction and comparison

The agreed target is the union of both implementations' capabilities. Preserve
working scanner behavior and add useful CoP coverage. Compare at component,
object, field and relationship level: an object type appearing in both tools
does not establish equivalent fields, value handling or associations.

| Where a capability exists | Required treatment |
| --- | --- |
| Only in this scanner | Retain it and its verification |
| Only in CoP | Reuse or integrate it after checking its actual behavior |
| In both | Compare semantics and preserve the required behavior from each |
| In neither | Report the remaining gap against AAP's configuration APIs |

In particular, preserve accepted baselines, conflict detection, review digests,
complete-visibility and deletion checks, named references, literal values,
protected secret preservation and code-owned workflow checks. Exporting an
object alone does not replace these extraction and comparison guarantees.
Deduplicating a capability list must not silently select between conflicting
configuration values or treat an omitted field as an explicit empty value.

Use one review process: discover live configuration, extract supported objects,
compare against the owning encrypted Git configuration, then capture reviewed
changes. Keep project repository and Vault selection explicit and bound to the
existing credentials. Deployment routing already exists; live capture into all
project companions is still unfinished.

Coverage must be assessed per component, object, field and relationship. Report
unsupported or unreadable areas explicitly. An absent endpoint, a denied read,
incomplete pagination or a masked value is not evidence of deletion or equality.
Do not count job history, conversation transcripts, metric samples or content
blobs as configuration merely because an API exposes them.

Preserve creation-time secrets in the owning private, per-instance Vault data
and reuse those protected inputs. A later API mask cannot verify a rotation.
Vault password files stay outside Git. Scanner expansion must not silently
change access controls, install new dependencies or apply live configuration.

Existing extraction and review behavior is documented in
[CaC reconciliation](cac-reconciliation.md). The extension remains implementation
work; the research and schema discovery above do not close that requirement.

[routing]: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/upgrade-con_upgrade_api_changes_27
[gateway-schema]: https://docs.redhat.com/it/documentation/red_hat_ansible_automation_platform/2.7/configure-con_gw_open_api_specification
[eda-schema]: https://github.com/ansible/eda-server/blob/main/README.md
[capture]: https://github.com/redhat-cop/aap_configuration_extended/blob/devel/docs/filetree_create_capture.md
[export-role]: https://github.com/redhat-cop/aap_configuration_extended/blob/devel/roles/filetree_create/README.md
[conversion]: https://github.com/redhat-cop/infra.aap_configuration/blob/devel/docs/CONVERSION_GUIDE.md
