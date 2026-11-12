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
A left sidebar holds chapter navigation, the four deployment stages, job status,
progress and presenter controls. The main diagram has three columns: compact
repositories, original AAP and new AAP. Repository windows are approximately
50 percent wider on a wide desktop, while the original AAP is narrower and
shorter. The two AAP cards share the same visual language; longer receiving
object lists scroll within the card. There is no marketing hero
or explanatory scene header above the diagram. Stage 02 is labelled **Prepare OS
for AAP installation**. Strong fills, borders and labelled badges distinguish the
origins. Active connectors use a bold directional line, brief travelling markers
and normal HTML action labels, avoiding stretched SVG text. Arrow strokes,
markers and labels share the highlighted code/object-origin colour: deployment
and base configuration remain blue, Git-defined additions use violet, and
captured manual definitions use amber. The highlighted YAML identifies the
definitions in focus; execution-code highlighting means code being read, not a
change to the public playbook. Reduced motion keeps the strong static activity cue.
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

## Verification

Use existing Node 18 or newer (verified with Node 22.23.1) and Python; no browser
or dependency installation is needed.

```sh
node --check demo/src/scenario.js
node --check demo/src/app.js
node --test demo/tests/walkthrough.test.cjs
node demo/tests/live.cjs https://kvegh.github.io/aap_autodeploy_configascode/
python3 -m http.server 8765 --directory demo --bind 127.0.0.1
```

Open the local URL only on the host running the server, or through an existing
supported forwarding mechanism. Next/Previous, the six chapter buttons, the
four stage buttons, arrow keys, R and restart navigate the same state. Source
links open the real implementation. Motion honours reduced-motion preferences.

The Node tests exercise the real scripts against a disposable DOM and check
visible object outcomes, source mapping, true hidden state and reversible
navigation. The live runner downloads only the five allowlisted assets over HTTPS, refuses
redirects, checks size/time limits and requires exact checkout byte parity before
executing the same interaction suite against the downloaded files. It removes
only its own temporary directory and exits nonzero for a failure. Run it from the
checkout matching the intended deployment; an older or not-yet-published checkout
will fail parity. No credentials or live AAP inputs are needed, and no remote data
is changed. These checks exercise deployed HTML/JavaScript interactions in a
disposable DOM; they do not establish rendered browser, desktop or phone layout.
The owner chose existing checks only; no browser installation is authorized.

## Publication

The retained `.github/workflows/deploy-demo.yml` checks the source and publishes
only `index.html`, `icon.svg`, `src/app.js`, `src/scenario.js`, `src/styles.css`
and a generated `.nojekyll`. Repository Pages must use GitHub Actions. A matching
main push deploys after checks; pull requests only check. There is no build step.
Source publication, GitHub Pages deployment and actual AAP execution are separate
outcomes and must be reported separately.
