# AAP CaC: two instances, one configuration story

A new buildless, browser-local visualization of the implemented AAP configuration
paths. The owner-selected presentation keeps configuration data separate from
execution code and follows two AAP instances through deployment, project imports,
Git-authored additions, manual UI additions and a return to encrypted CaC.

Six chapters contain nine presenter-controlled stops because the deployment
chapter gives all four stages their own view. The receiving platform is genuinely
hidden initially; Stage 01 reveals a RHEL VM, Stage 03 reveals AAP, and Stage 04
reveals only the shared base objects. Additional project definitions follow.
Backwards navigation, restart and direct links restore the corresponding state.

The interface uses a light canvas and labelled origin colours: blue for base
objects, violet for Git-defined additions and amber for manually created objects.
Captured manual objects keep their origin and gain an **In Git** badge. The
private repository carries a lock; its YAML is an illustrative decrypted view,
not ciphertext rendered as readable text. All examples are synthetic.

## Code and data

`src/scenario.js` contains the story, object fixtures and source links. `src/app.js`
renders the state and navigation. Native browser DOM APIs are sufficient for this
static educational interaction; Ansible modules are not a browser renderer.
There are no external scripts, packages, fonts, analytics, API calls or runtime
services. No live AAP or Git operation is performed by the page.

The public execution preview uses condensed excerpts from the actual playbooks
and configuration roles. Source citations pin the inspected runtime logic at
`20f70af1c9006a06d422ffa368d38a9f25ae2e13`; that source pin is separate from the
new visualization's own publication revision. Human-facing job labels describe
the operation, rather than inventing new deployed Job Templates.

| Scene | Maintained source |
|---|---|
| Private definitions and public execution code | `tasks/cac-project-checkout.yml`, `tasks/cac-resource-definitions.yml` |
| VM, infrastructure, installer and shared base | `01-linux-vm-setup.yml` through `04-aap-config.yml` |
| Project objects and later Git-defined additions | `deploy-cac-project.yml`, `tasks/cac-resource-definitions.yml` |
| Manual changes returning to configuration | `capture-aap-cac.yml`, `docs/cac-reconciliation.md` |

As requested, the story abstracts the application trigger and detailed scan/review
mechanics. It does not change those mechanisms: imports and captures remain
explicit operations in the actual implementation. The existing capture adapter
has its documented Controller scope: the scene assumes supported, owned objects.
Credential secrets are maintained separately through protected inputs; scanning
cannot recover newly masked passwords or tokens. The page does not establish
universal AAP export, live deployment or workload acceptance.

## Checks and local preview

Use existing Node and Python; do not install a browser or dependency for this demo.

```sh
node --check demo/src/scenario.js
node --check demo/src/app.js
node --test demo/tests/walkthrough.test.cjs
python3 -m http.server 8765 --directory demo --bind 127.0.0.1
```

Open the local URL only on the host running the server, or through an existing
supported forwarding mechanism. Next/Previous, the six chapter buttons, the
four stage buttons, arrow keys, R and restart navigate the same state. Source
links open the real implementation. Motion honours reduced-motion preferences.

The Node tests exercise the real scripts against a disposable DOM and check
visible object outcomes, source mapping, true hidden state and reversible
navigation. After publication, the repeatable deployed check downloads the five
public assets over HTTPS, runs the same interactions against those downloaded
HTML/JavaScript bytes and cleans up its temporary fixtures:

```sh
node demo/tests/live.cjs https://kvegh.github.io/aap_autodeploy_configascode/
```

This requires network access to that Pages site and the existing checkout for
source references. It returns a nonzero status for failed downloads or
interactions. It changes no remote resources. These checks do not establish
rendered browser, desktop or phone layout.
The owner chose existing checks only; no browser installation is authorized.

## Publication

The retained `.github/workflows/deploy-demo.yml` checks the source and publishes
only `index.html`, `icon.svg`, `src/app.js`, `src/scenario.js`, `src/styles.css`
and a generated `.nojekyll`. Repository Pages must use GitHub Actions. A matching
main push deploys after checks; pull requests only check. There is no build step.
Source publication, GitHub Pages deployment and actual AAP execution are separate
outcomes and must be reported separately.
