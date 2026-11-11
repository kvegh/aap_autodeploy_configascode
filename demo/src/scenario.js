(function (root) {
  'use strict';

  const sourceRevision = 'e371c76c4d8e102f152e3a41ccfb76184fa91580';
  const sourceRoot = `https://github.com/kvegh/aap_autodeploy_configascode/blob/${sourceRevision}/`;
  const steps = [
    {
      id: 'overview', phase: 'The idea', title: 'Build the AAP. Keep the knowledge.',
      view: 'deployment', deploymentFocus: ['runner', 'host'],
      description: 'Follow the normal journey: create a VM, prepare DNS and TLS, install AAP, then configure its base and selected projects from reviewed code and encrypted inputs.',
      focus: ['code', 'desired', 'source', 'target'], routes: [], configured: [],
      caption: 'Four deployment stages establish the platform. Reviewed project CaC builds its automation catalog.',
      heading: 'Two kinds of input. One repeatable approach.',
      body: 'An existing source AAP runs the deployment jobs against the pinned test hypervisor and new guest. Once AAP is installed, configuration jobs apply reviewed definitions through the receiving platform’s API.',
      points: ['The four existing stages cover VM creation, infrastructure, AAP installation and Base AAP configuration.', 'Shared base and selected project captures retain protected inputs in encrypted configuration.', 'The page illustrates code behavior. It runs no jobs, and physical-host deployment is outside this story.'],
      codeTitle: 'The configuration entry points',
      code: '01-linux-vm-setup.yml   # create the new VM\n02-infra-config.yml     # DNS, TLS and nginx\n03-aap-install.yml      # install AAP\n04-aap-config.yml       # shared platform base\n\ndeploy-cac-project.yml  # selected project definitions',
      sources: ['01-linux-vm-setup.yml', '02-infra-config.yml', '03-aap-install.yml', '04-aap-config.yml'],
      next: 'Choose the destination',
    },
    {
      id: 'destination', phase: 'Select', title: 'Make each destination explicit.',
      view: 'deployment', deploymentFocus: ['runner', 'host'],
      description: 'First select and verify the test hypervisor. The source AAP will create its new guest there; later, configuration jobs will use the installed AAP’s verified API.',
      focus: ['source', 'target'], routes: ['apply'], configured: [],
      caption: 'An existing source AAP → one explicitly pinned test hypervisor. The new guest comes next.',
      heading: 'The execution platform and the target have different roles.',
      body: 'Stage 01 requires one independently pinned test hypervisor. The returned instance key and protected registered route select the same guest for later stages. Project imports use the selected inventory instance’s saved API access.',
      points: ['The hypervisor’s actual machine identity and trusted SSH keys must match before writes.', 'API access must agree with inventory; missing, expired or mismatched access stops import and TLS verification stays enabled.', 'A project import may configure the source AAP itself or another verified AAP. This choice does not create a VM.'],
      codeTitle: 'Illustrative operator selection',
      code: 'aap_hypervisor_pin:\n  machine_id: <verified test-host identity>\n\n# Stage 01 reserves the next instance name.\n# Later stages select that same registered guest.',
      sources: ['tasks/aap-hypervisor-identity.yml', 'tasks/aap-instance-select.yml', 'tasks/cac-api-auth.yml', 'filter_plugins/use_case_setup.py'],
      next: 'Open the reviewed inputs',
    },
    {
      id: 'inputs', phase: 'Read', title: 'Keep automation and protected inputs together in purpose.',
      view: 'deployment', deploymentFocus: ['runner', 'host'],
      description: 'The job reads the reviewed automation and the correct encrypted configuration. Git and Vault credentials are supplied by AAP; the checkout is temporary.',
      focus: ['code', 'desired', 'source'], routes: ['code', 'desired'], configured: [],
      caption: 'Public playbooks + private desired configuration → one protected job workspace.',
      heading: 'Shared base and project configuration have different homes.',
      body: 'Base reads the shared platform capture. Each project importer derives its own companion repository and canonical capture from the fixed project ID. Free-form repository and file overrides are refused.',
      points: ['Base: cac/base_CaC_vault.yml.', 'Project: vaults/cac/<project-id>-cac-vault.yml.', 'The project’s saved Git/Vault credentials protect its checkout and decryption.'],
      codeTitle: 'The fixed project capture route',
      code: 'project ID\n  → <project-id>-secrets repository\n  → vaults/cac/<project-id>-cac-vault.yml\n\n# Decrypt only inside the private job workspace.',
      sources: ['tasks/cac-project-checkout.yml', 'filter_plugins/cac_import.py', 'tasks/private-config-cleanup.yml'],
      next: 'Create the new VM',
    },
    {
      id: 'vm', phase: 'Stage 01 / VM deployment', title: 'Create one new VM on the pinned test host.',
      description: 'The source AAP proves the test hypervisor and its isolation, reserves one global name in encrypted state, then copies the verified golden image to a new disk.',
      view: 'deployment', stage: 1,
      focus: [], routes: [], configured: [],
      deploymentFocus: ['runner', 'state', 'host', 'guest'], deploymentRoutes: ['reserve', 'ssh', 'copy'], deploymentReady: ['state', 'guest'],
      caption: '01-linux-vm-setup.yml: pinned host → encrypted reservation → new golden-image copy → fresh guest identity.',
      heading: 'A new guest, with its own identity.',
      body: 'The existing golden image is preserved. Only this job’s newly copied disk is resized and customized. Fresh SSH host keys are provisioned, the guest machine identity is renewed, and the running guest is verified through its exact pinned route.',
      points: ['The selected test host, production protections and complete live isolation policy must pass before reservation or disk changes.', 'Existing domain or disk collisions are refused. The encrypted global counter advances; the old local counter is read, not rewritten.', 'The published instance key and route carry this exact guest into the following stages.'],
      codeTitle: 'The existing golden-image copy',
      code: '- name: Copy the saved golden image only to this new disk\n  ansible.builtin.copy:\n    src: "{{ aap_golden_image_path }}"\n    dest: "{{ vm_dir }}/{{ vm_name }}.disk.qcow2"\n    remote_src: true\n    force: false\n    mode: preserve',
      sources: ['01-linux-vm-setup.yml', 'tasks/aap-hypervisor-pin.yml', 'tasks/aap-hypervisor-identity.yml'],
      next: 'Prepare DNS, TLS and the proxy',
    },
    {
      id: 'infrastructure', phase: 'Stage 02 / Infrastructure', title: 'Give that guest its trusted public entrance.',
      description: 'The next job resolves the same registered guest, rechecks its pinned hypervisor, then prepares the reserved DNS name, public certificate and nginx frontend.',
      view: 'deployment', stage: 2,
      focus: [], routes: [], configured: [],
      deploymentFocus: ['runner', 'host', 'edge'], deploymentRoutes: ['ssh', 'dns'], deploymentReady: ['state', 'guest', 'edge'],
      caption: '02-infra-config.yml: reserved DNS name → existing approved ACME registration → validated TLS frontend.',
      heading: 'Public TLS first; a verified upstream follows installation.',
      body: 'DNS changes must agree with the registered route, and conflicting records are refused. Certificate readiness and an existing approved ACME account or certificate are required. nginx is validated before reload; its TLS frontend waits for authenticated installer trust.',
      points: ['This stage does not register an ACME account or accept new legal terms. Missing approval prerequisites stop it.', 'The frontend returns a temporary 503 while the installed AAP upstream is not yet trusted.', 'DNS and proxy changes remain bound to this guest’s reserved name and pinned hypervisor.'],
      codeTitle: 'The existing frontend readiness state',
      code: '- name: Deploy the TLS frontend pending authenticated installer trust\n  ansible.builtin.template:\n    src: templates/nginx-aap-test.conf.j2\n    dest: "/etc/nginx/conf.d/{{ vm_name }}.conf"\n  vars:\n    aap_upstream_ready: false',
      sources: ['02-infra-config.yml', 'templates/nginx-aap-test.conf.j2', 'tasks/aap-instance-select.yml'],
      next: 'Install AAP in the guest',
    },
    {
      id: 'installation', phase: 'Stage 03 / AAP installation', title: 'Install the platform inside the verified guest.',
      description: 'The source job prepares the selected RHEL guest through strict SSH trust, runs the containerized AAP installer, and verifies the resulting Gateway and public endpoint.',
      view: 'deployment', stage: 3,
      focus: [], routes: [], configured: [],
      deploymentFocus: ['runner', 'guest', 'platform', 'edge'], deploymentRoutes: ['ssh', 'install', 'frontend'], deploymentReady: ['state', 'guest', 'edge', 'platform'],
      caption: '03-aap-install.yml: strict guest SSH → containerized installer → authenticated CA readback → verified public Gateway.',
      heading: 'Installation success is checked before the proxy opens upstream.',
      body: 'The stage checks the guest’s supported filesystem layout and available capacity, prepares its repositories, and runs the existing installer bundle. After successful installation it verifies Gateway using the authenticated local CA, then publishes and checks the trusted upstream through nginx.',
      points: ['The registered route and pinned guest host keys determine SSH access; an arbitrary scanned key is not accepted.', 'The normal installer has a bounded async run. The existing observer can check that same installer result without starting another.', 'A reachable web page alone is insufficient: the final public response must identify an actual Controller.'],
      codeTitle: 'The actual installer invocation',
      code: '- name: Run AAP installer\n  ansible.builtin.command:\n    cmd: ansible-playbook -i inventory ansible.containerized_installer.install\n    chdir: "{{ installer_extract_dir }}/{{ installer_dir_name }}"\n  async: 7200\n  poll: 30\n  changed_when: true',
      sources: ['03-aap-install.yml', 'tasks/aap-instance-ssh.yml', 'tasks/aap-upstream-trust.yml'],
      next: 'Apply Base AAP configuration',
    },
    {
      id: 'base', phase: 'Stage 04 / Base AAP configuration', title: 'Give the installed AAP its common foundation.',
      stage: 4,
      description: 'Base configuration prepares the shared AAP capabilities: organizations, platform settings, credentials and Automation Hub configuration. It also prepares access for later configuration jobs.',
      focus: ['desired', 'source', 'target'], routes: ['desired', 'apply'], configured: ['base'],
      caption: '04-aap-config.yml applies shared configuration through infra.aap_configuration.',
      heading: 'A configured base makes later imports possible.',
      body: 'The base stage applies the subscription, creates organizations before their Hub credentials, and applies shared definitions through the configuration collection. It provisions the declared Git/Vault bootstrap credentials and prepares persistent API/MCP access.',
      points: ['Automation Hub repository and retention settings belong to the base.', 'Persistent instance access can be published to encrypted CaC and the existing source credential.', 'The base job removes its temporary checkout and revokes its temporary Gateway token.'],
      codeTitle: 'Existing base configuration role',
      code: '- name: Apply shared AAP configuration\n  ansible.builtin.include_role:\n    name: infra.aap_configuration.dispatch\n  vars:\n    dispatch_include_wildcard_vars: false',
      sources: ['04-aap-config.yml', 'tasks/bootstrap-credentials.yml', 'tasks/mcp-access.yml'],
      next: 'Choose the project definitions',
    },
    {
      id: 'selection', phase: 'Choose', title: 'Add the use cases you actually need.',
      description: 'Choose reviewed project configurations, such as disconnected Windows patching or AIOps. The selector prepares their declared prerequisites and calls their existing CaC job templates.',
      focus: ['code', 'desired', 'source', 'target'], routes: ['code', 'desired', 'apply'], configured: ['base'],
      caption: 'Selected projects share one importer; each keeps its own reviewed capture and credentials.',
      heading: 'Select several projects, or import one directly.',
      body: 'deploy-selected-use-cases.yml orchestrates deliberate selections and prerequisite preparation. Each saved “Deploy … CaC” template calls deploy-cac-project.yml directly with its fixed project ID. The standalone importer can also be run on its own.',
      points: ['Unknown, duplicate and unavailable selections are refused.', 'Declared collection dependencies are prepared in Automation Hub when needed.', 'Existing, remote and self-target AAP instances are supported; preparation retains its registered-route checks.'],
      codeTitle: 'One shared importer, project-specific inputs',
      code: '# Saved by the project’s CaC job template:\naap_cac_project_id: disconnected-windows-patching\n\n# The common entry point:\nplaybook: deploy-cac-project.yml',
      sources: ['vars/use-case-catalog.yml', 'deploy-selected-use-cases.yml', 'tasks/selected-use-case-import.yml'],
      next: 'Validate, then import',
    },
    {
      id: 'import', phase: 'Apply', title: 'Check the definitions. Then build their dependencies.',
      description: 'The importer validates capture identity, declared inputs, resource mappings and template labels before applying project objects through the target API.',
      focus: ['source', 'target'], routes: ['apply'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Dependencies first: ordinary resources → group relationships → templates → workflows → declared EDA definitions.',
      heading: 'An ordered import, with a clear scope.',
      body: 'Only the capture’s explicitly mapped resources are imported. Configuration roles handle the ordinary resources; all group skeletons exist before relationships, job templates precede their workflows, and EDA dependencies precede activation definitions.',
      points: ['Project configuration does not use ambient wildcard variable merging.', 'Required labels and declared readiness checks must pass before resource changes.', 'Existing secret access is preserved where supported; AIOps preparation/readback updates only its selected saved settings.'],
      codeTitle: 'A dependency expressed in the actual importer',
      code: '- name: Import workflow definitions after all referenced job templates\n  ansible.builtin.include_role:\n    name: infra.aap_configuration.controller_workflow_job_templates\n  when: controller_workflows | length > 0',
      sources: ['deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml', 'tasks/cac-template-labels.yml'],
      next: 'See what “configured” means',
    },
    {
      id: 'configured', phase: 'Use', title: 'The catalog is ready. Workloads have their own start.',
      description: 'Projects, inventories, credentials, templates and workflows are now definitions in AAP. Running the application or a deployment workflow remains a separate operator action.',
      focus: ['target'], routes: [], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Configuration import creates the automation catalog; application execution is a separate action.',
      heading: 'A useful boundary between defining and running.',
      body: 'The project importer excludes job launches, workflow launches, schedules and resource deletion. New EDA activation definitions are created disabled, while existing activation states are preserved.',
      points: ['Importing Windows configuration does not start patching.', 'Importing AIOps configuration does not launch the recovery demo.', 'Removing a definition from CaC does not itself delete the corresponding live object.'],
      codeTitle: 'Existing application-launch exclusions',
      code: 'aap_configuration_dispatcher_exclude_roles:\n  - controller_job_launch\n  - controller_workflow_launch\n\n# EDA definitions are handled separately:\nrestart: false',
      sources: ['tasks/cac-resource-definitions.yml', 'filter_plugins/cac_import.py', 'action_plugins/aap_cac_activation.py'],
      next: 'Review later changes',
    },
    {
      id: 'capture', phase: 'Review', title: 'Bring reviewed changes back into configuration.',
      description: 'The existing scoped capture reads Controller configuration and compares it with encrypted CaC. Preview comes first, with an encrypted report for human review.',
      focus: ['desired', 'target', 'review'], routes: ['review', 'save'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Controller → scoped read-only preview → review → an explicitly accepted encrypted Git update.',
      heading: 'A reviewed return path, with defined limits.',
      body: 'The current capture adapter covers an explicitly owned AutoDeploy Controller scope. It checks visibility and conflicts against accepted baselines. A reviewed digest binds a proposed update to the inputs and source revision.',
      points: ['First baseline initialization and later updates are explicit choices.', 'Commit and push default to false; preview does not change AAP.', 'Gateway, EDA and Automation Hub are outside this capture adapter. Masked secret rotations need a separate protected input update.'],
      codeTitle: 'The default capture mode',
      code: 'aap_cac_capture_scope: autodeploy\naap_cac_capture_mode: preview\naap_cac_capture_commit: false\naap_cac_capture_push: false',
      sources: ['capture-aap-cac.yml', 'docs/cac-reconciliation.md', 'src/cac_compare.py'],
      next: 'See the complete picture',
    },
    {
      id: 'complete', phase: 'The complete picture', title: 'Keep the platform’s knowledge ready for its next home.',
      description: 'Reviewed automation, encrypted desired configuration and explicit destination access make the configuration reusable. Each import has a defined target, a defined scope and a result to verify.',
      focus: ['code', 'desired', 'source', 'target', 'review'], routes: ['code', 'desired', 'apply', 'review', 'save'], configured: ['base', 'inventory', 'templates', 'eda'],
      caption: 'Describe → validate → configure → review. Reuse the same configuration approach on the selected AAP.',
      heading: 'Recreation is an outcome to verify.',
      body: 'These are implemented configuration paths. A successful import proves the selected definitions were installed. Complete environment recovery and production takeover require their own functional verification.',
      points: ['Maintain shared settings separately from instance-specific values.', 'Keep protected inputs encrypted and use the selected instance’s access.', 'Verify configuration results, then deliberately run and test the required workloads.'],
      codeTitle: 'Keep exploring the actual source',
      code: 'Shared foundation  →  04-aap-config.yml\nProject import     →  deploy-cac-project.yml\nSelection          →  deploy-selected-use-cases.yml\nReviewed capture   →  capture-aap-cac.yml',
      sources: ['docs/cac-project-import.md', 'docs/selected-use-cases.md', 'docs/cac-reconciliation.md'],
      next: 'Start again',
    },
  ];

  function stepAt(index) {
    if (!Number.isInteger(index)) throw new TypeError('Step index must be an integer.');
    return steps[Math.max(0, Math.min(steps.length - 1, index))];
  }

  function move(index, direction) {
    if (!Number.isInteger(index) || ![-1, 1].includes(direction)) throw new TypeError('Choose a valid step and direction.');
    return Math.max(0, Math.min(steps.length - 1, index + direction));
  }

  const api = { steps, stepAt, move, sourceRevision, sourceRoot, runtimeVersion: '0.50.13' };
  function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
  }
  freeze(api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CacWalkthrough = api;
}(typeof globalThis !== 'undefined' ? globalThis : this));
