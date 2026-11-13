/* Story and illustrative objects. Source mapping and scope: ../README.md#code-and-data. */
(function (root) {
  'use strict';
  const sourceRevision = 'f52546d3456614869aa254d220de4a786b96c31f';
  const sourceRoot = `https://github.com/kvegh/aap_autodeploy_configascode/blob/${sourceRevision}/`;
  const baseObjects = [
    { id: 'platform', type: 'Inventories', name: 'VMWare Inventory', origin: 'base' },
    { id: 'platform-code', type: 'Projects', name: 'AAP Config-as-Code Git', origin: 'base' },
    { id: 'managed-access', type: 'Credentials', name: 'Server access key', origin: 'base' },
    { id: 'platform-jobs', type: 'Job Templates', name: 'AAP Config-as-Code jobs', origin: 'base' },
  ];
  const baseConfiguration = [
    { id: 'logging', name: 'AAP Logging Config v1', origin: 'base', version: 1 },
    { id: 'eda', name: 'AAP EDA Config v1', origin: 'base', version: 1 },
  ];
  const baseInfrastructure = [
    { id: 'certificate', name: 'Certificate config v1', origin: 'base', version: 1 },
    { id: 'firewall', name: 'Firewall Config v1', template: 'Configure firewall', origin: 'base', version: 1 },
  ];
  const projectObjects = [
    { id: 'operations', type: 'Inventories', name: 'Satellite Inventory', origin: 'git' },
    { id: 'app-code', type: 'Projects', name: 'Application automation playbooks', origin: 'git' },
    { id: 'app-access', type: 'Credentials', name: 'Application auth token', origin: 'git' },
    { id: 'app-jobs', type: 'Job Templates', name: 'Deploy application', origin: 'git' },
    { id: 'regional', type: 'Inventories', name: 'Regional servers', origin: 'git' },
    { id: 'regional-code', type: 'Projects', name: 'Regional automation', origin: 'git' },
  ];
  const manualObjects = [
    { id: 'emergency', type: 'Inventories', name: 'Emergency servers', origin: 'manual' },
    { id: 'quick-fix', type: 'Projects', name: 'Quick-fix automation', origin: 'manual' },
    { id: 'temporary-access', type: 'Credentials', name: 'Temporary access', origin: 'manual' },
  ];
  const steps = [
    { id: 'separation', chapter: 'separation', title: 'Data & code', description: 'Private configuration and public playbooks feed the original AAP.', stage: 0, job: 'Ready to deploy', status: 'Source AAP', routes: [], sources: ['tasks/cac-project-checkout.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'vm', chapter: 'deployment', title: '01 / Create a new home.', description: 'The original AAP creates a RHEL VM on the prepared host. It is a new guest, with no AAP content yet.', stage: 1, job: '01 · Create VM', status: 'VM created', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['01-linux-vm-setup.yml'] },
    { id: 'infrastructure', chapter: 'deployment', title: 'Prepare OS for AAP installation', description: 'DNS, TLS certificates and nginx connect that same guest to its reserved address. The VM is ready for AAP installation.', stage: 2, job: '02 · Prepare OS for AAP installation', status: 'OS prepared for AAP installation', routes: ['flow-code', 'flow-apply'], sources: ['02-infra-config.yml'] },
    { id: 'installation', chapter: 'deployment', title: '03 / Install AAP inside the VM.', description: 'The platform is installed in the new guest. A second AAP now exists; its automation catalogue comes next.', stage: 3, job: '03 · Install AAP', status: 'AAP installed', routes: ['flow-code', 'flow-apply'], sources: ['03-aap-install.yml'] },
    { id: 'base-rhel', chapter: 'deployment', title: 'RHEL configuration', description: 'Apply the initial RHEL configuration profiles: Certificate config v1 and Firewall Config v1. The installed AAP has no shared settings or imported automation objects yet.', stage: 4, baseFocus: 'rhel', job: 'Apply RHEL configuration', status: 'RHEL configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['02-infra-config.yml'] },
    { id: 'base-aap', chapter: 'deployment', title: 'AAP configuration', description: 'Apply AAP Logging Config v1 and AAP EDA Config v1. RHEL configuration is retained; shared automation objects come next.', stage: 4, baseFocus: 'aap', job: 'Apply AAP configuration', status: 'AAP configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['04-aap-config.yml'] },
    { id: 'base', chapter: 'deployment', title: 'AAP content', description: 'Import the shared inventories, projects, credentials and Job Templates. The initial RHEL configuration, AAP settings and base automation content are now applied.', stage: 4, baseFocus: 'content', job: 'Import base AAP content', status: 'Base configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['04-aap-config.yml'] },
    { id: 'project', chapter: 'project', title: 'Turn definitions into more automation.', description: 'A configuration Job Template on the original AAP combines the private YAML with the public playbooks. Additional objects appear on the receiving AAP.', stage: 4, job: 'Deploy objects', status: 'Project objects applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'git-change', chapter: 'git-change', title: 'New requirements? Change the YAML.', description: 'Your team updates AAP Logging Config v1 to v2 in CaC. The original AAP applies the settings change; AAP EDA Config v1 and the imported automation objects stay unchanged.', stage: 4, job: 'Apply configuration', status: 'AAP Logging Config v2 applied; AAP EDA Config v1 unchanged', routes: ['flow-config', 'flow-code', 'flow-apply'], actor: ['Configuration author', 'Updates AAP Logging Config to v2. AAP EDA Config v1 and the imported objects are retained.'], sources: ['04-aap-config.yml'] },
    { id: 'infra-change', chapter: 'git-change', title: 'Apply infrastructure configuration.', description: 'CaC updates the RHEL infrastructure configuration: Certificate config becomes purple v2, while Firewall Config stays blue v1.', stage: 4, job: 'Apply infrastructure configuration', status: 'Certificate v2 applied; firewall v1 unchanged', routes: ['flow-config', 'flow-code', 'flow-apply'], actor: ['Infrastructure author', 'Updates Certificate config to v2 and retains Firewall Config v1.'], sources: ['02-infra-config.yml', 'deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'manual', chapter: 'manual', title: 'Sometimes, changes happen in the UI.', description: 'An operator adds an inventory, project and credential directly on the receiving AAP. They exist there now, but their definitions are not in Git yet.', stage: 4, job: 'Ready to scan configuration', status: 'Manual objects added', routes: [], actor: ['Sysadmin · incident response', 'Responds to an outage and creates objects directly in the receiving AAP.'], sources: ['capture-aap-cac.yml'] },
    { id: 'capture', chapter: 'capture', title: 'Bring those changes back into Git.', description: 'A configuration scan Job Template on the original AAP reads the added objects and brings their definitions into the encrypted CaC. The next setup can use them too.', stage: 4, job: 'Scan AAP configuration', status: 'Added definitions recorded in Git', routes: ['flow-scan', 'flow-return'], sources: ['capture-aap-cac.yml', 'docs/cac-reconciliation.md'] },
    { id: 'next-aap', chapter: 'rebuild', title: 'Ready for another AAP.', description: 'The complete configuration is now in Git. Prepare the next destination, then deploy another AAP from those saved definitions.', stage: 4, job: 'Ready for the next deployment', status: 'Configuration ready to reuse', routes: [], sources: ['01-linux-vm-setup.yml'] },
    { id: 'rebuild', chapter: 'rebuild', title: 'Deploy the complete configuration again.', description: 'The original AAP creates another AAP from the configuration now kept in Git: base definitions, Git changes and captured manual additions, with AAP Logging Config v2, AAP EDA Config v1, Certificate config v2 and Firewall Config v1.', stage: 4, job: 'Rebuild from Git', status: 'Another AAP restored from Git', routes: ['flow-config', 'flow-code', 'flow-rebuild'], sources: ['01-linux-vm-setup.yml', '02-infra-config.yml', '03-aap-install.yml', '04-aap-config.yml', 'deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
  ];
  const stepPositions = Object.fromEntries(steps.map((step, position) => [step.id, position]));
  const chapters = [
    ['separation', 'Data & code'], ['deployment', 'A new AAP'],
    ['project', 'Apply objects'], ['git-change', 'Change in Git'],
    ['manual', 'Change in AAP'], ['capture', 'Back to Git'], ['rebuild', 'Deploy again'],
  ].map(([id, title]) => ({ id, title, index: steps.findIndex(step => step.chapter === id) }));
  function stateAt(index) {
    if (!Number.isInteger(index)) throw new TypeError('Step index must be an integer.');
    const position = Math.max(0, Math.min(steps.length - 1, index));
    const step = steps[position];
    const rhelConfigurationApplied = position >= stepPositions['base-rhel'];
    const aapConfigurationApplied = position >= stepPositions['base-aap'];
    const baseContentApplied = position >= stepPositions.base;
    const targetObjects = [
      ...(baseContentApplied ? baseObjects : []), ...(position >= stepPositions.project ? projectObjects : []),
      ...(position >= stepPositions.manual ? manualObjects : []),
    ].map(object => ({ ...object, inGit: object.origin !== 'manual' || position >= stepPositions.capture }));
    const configObjects = [...baseObjects, ...projectObjects, ...(position >= stepPositions.capture ? manualObjects : [])];
    // Replace one stable configuration entry; preserve EDA and the source's state.
    const desiredConfiguration = baseConfiguration.map(config => config.id === 'logging' && position >= stepPositions['git-change']
      ? { ...config, name: 'AAP Logging Config v2', origin: 'git', version: 2 }
      : { ...config });
    const sourceConfiguration = baseConfiguration.map(config => ({ ...config }));
    const targetConfiguration = aapConfigurationApplied ? desiredConfiguration.map(config => ({ ...config })) : [];
    const desiredInfrastructure = baseInfrastructure.map(config => config.id === 'certificate' && position >= stepPositions['infra-change']
      ? { ...config, name: 'Certificate config v2', origin: 'git', version: 2 }
      : { ...config });
    const sourceInfrastructure = baseInfrastructure.map(config => ({ ...config }));
    const targetInfrastructure = step.stage >= 2 ? desiredInfrastructure.map(config => ({ ...config })) : [];
    const rebuilding = step.id === 'rebuild';
    // Replay the saved definitions, including captured manual origins, into a fresh platform.
    const successorObjects = rebuilding ? configObjects.map(object => ({ ...object, inGit: true })) : [];
    const successorConfiguration = rebuilding ? desiredConfiguration.map(config => ({ ...config })) : [];
    const successorInfrastructure = rebuilding ? desiredInfrastructure.map(config => ({ ...config })) : [];
    const flowOrigin = rebuilding ? 'mixed' : position >= stepPositions.manual ? 'manual' : position >= stepPositions.project ? 'git' : 'base';
    return {
      index: position, step, flowOrigin, rebuilding,
      rhelConfigurationApplied, aapConfigurationApplied, baseContentApplied,
      successorPlaceholderVisible: step.id === 'next-aap',
      successorVisible: rebuilding, successorObjects, successorConfiguration, successorInfrastructure,
      desiredConfiguration, sourceConfiguration, targetConfiguration,
      desiredInfrastructure, sourceInfrastructure, targetInfrastructure,
      targetObjects, configObjects,
      sourceObjects: baseObjects.map(object => ({ ...object, inGit: true })),
      targetVisible: step.stage > 0, captured: position >= stepPositions.capture,
    };
  }
  function configurationLines(state) {
    const fields = [['Inventories', 'controller_inventories'], ['Projects', 'controller_projects'], ['Credentials', 'controller_credentials'], ['Job Templates', 'controller_templates']];
    const lines = [{ text: '# Illustrative decrypted view · stored encrypted', origin: 'base' }];
    const logging = state.desiredConfiguration.find(config => config.id === 'logging');
    const readingConfiguration = state.step.routes.includes('flow-config');
    const baseFocus = state.step.baseFocus;
    const readingAapConfiguration = readingConfiguration && (!baseFocus || baseFocus === 'aap');
    const readingRhelConfiguration = readingConfiguration && (!baseFocus || baseFocus === 'rhel');
    const loggingActive = readingAapConfiguration && state.step.id !== 'infra-change' && (state.rebuilding || logging.origin === state.flowOrigin);
    const edaActive = readingAapConfiguration && (state.rebuilding || state.flowOrigin === 'base');
    for (const text of [
      `# ${logging.name}`,
      'controller_settings_base:',
      '  settings:',
      `    LOG_AGGREGATOR_ACTION_QUEUE_SIZE: ${logging.version === 1 ? 10000 : 20000}`,
    ]) lines.push({ text, origin: logging.origin, active: loggingActive });
    for (const text of [
      '# AAP EDA Config v1 · illustrative configuration excerpt',
      'eda_decision_environments_base:',
      '  - name: Event runtime',
      '    image_url: <decision-environment-image>',
      'eda_rulebook_activations_base:',
      '  - name: Event policy',
      '    decision_environment: Event runtime',
      '    log_level: info',
    ]) lines.push({ text, origin: 'base', active: edaActive });

    const certificate = state.desiredInfrastructure.find(config => config.id === 'certificate');
    const certificateActive = readingRhelConfiguration && (state.rebuilding || state.step.id === 'infra-change' || state.flowOrigin === 'base');
    for (const text of [
      `# RHEL infrastructure · ${certificate.name}`,
      `aap_upstream_hostname: ${certificate.version === 1 ? '<automation-service-name>' : '<updated-automation-service-name>'}`,
    ]) lines.push({ text, origin: certificate.origin, active: certificateActive });

    for (const [type, key] of fields) {
      lines.push({ text: `${key}:`, origin: 'base' });
      if (type === 'Job Templates') {
        // These are saved job inputs; importing them does not run infrastructure changes.
        for (const config of state.desiredInfrastructure.filter(config => config.template)) {
          const active = readingRhelConfiguration && (state.rebuilding || state.step.id === 'infra-change' && config.id === 'certificate' || state.flowOrigin === 'base');
          for (const text of [
            `  # ${config.name} · illustrative job inputs`,
            `  - name: ${config.template}`,
            '    extra_vars:',
            `      config_revision: v${config.version}`,
          ]) lines.push({ text, origin: config.origin, active });
        }
      }
      for (const object of state.configObjects.filter(item => item.type === type)) {
        const added = object.origin === 'manual';
        const readingConfiguration = state.step.routes.includes('flow-config') || state.step.routes.includes('flow-return');
        const focusedObject = (!baseFocus || baseFocus === 'content') && state.step.id !== 'infra-change' && state.step.id !== 'git-change' && (state.rebuilding || object.origin === state.flowOrigin);
        const active = readingConfiguration && focusedObject;
        lines.push({ text: `  - name: ${object.name}`, origin: object.origin, added, active });
        if (type === 'Projects') lines.push({ text: '    scm_url: <automation-repository>', origin: object.origin, added, active });
      }
      if (type === 'Inventories') lines.push(
        { text: 'controller_inventory_sources:', origin: 'base' },
        { text: '  - name: VMWare Inventory source', origin: 'base' },
        { text: '    inventory: VMWare Inventory', origin: 'base' },
        { text: '    source: scm', origin: 'base' },
      );
    }
    lines.push({ text: '# API access uses verified HTTPS', origin: 'base' });
    return lines;
  }
  function executionLines(state) {
    const stage = state.step.stage;
    if (state.step.id === 'capture') return ['# Accepted update · illustrative job inputs', 'aap_cac_capture_mode: update', 'aap_cac_capture_commit: true', 'aap_cac_capture_push: true', '', '# Implementation: capture-aap-cac.yml'];
    if (state.step.id === 'manual') return ['# capture-aap-cac.yml · excerpt', '- name: Extract and compare through protected Vault API and Git inputs', '  aap_cac_capture:', '    scope: "{{ aap_cac_capture_scope }}"'];
    if (state.step.baseFocus === 'aap' || state.step.id === 'git-change' || state.rebuilding) {
      const lines = ['# Platform settings · 04-aap-config.yml', '- name: Apply shared AAP configuration', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch', '  vars:', '    dispatch_include_wildcard_vars: false'];
      // Only the final replay combines platform settings with project imports.
      if (state.rebuilding) lines.push('', '# Project objects · tasks/cac-resource-definitions.yml', '- name: Import ordinary configuration resources without wildcard merging or workload execution', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch');
      return lines;
    }
    if (state.step.id === 'infra-change') return ['# Certificate configuration · 02-infra-config.yml', '- name: "Configure DNS, certificate, and nginx reverse proxy"', '  hosts: hypervisor', '  become: true', '  gather_facts: false', '', '# Infrastructure Job Template definitions · excerpt', '- name: Import job templates after their persistent credential dependencies', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.controller_job_templates'];
    if (stage === 1 || state.step.id === 'next-aap') return ['# 01-linux-vm-setup.yml · excerpt', '- name: Create a test VM only after shared name reservation and pinned rebuild preflight', '  hosts: hypervisor', '  become: true', '  gather_facts: false'];
    if (state.index >= stepPositions.project || state.step.id === 'separation') return ['# Inventories, projects and credentials · excerpt', '- name: Import ordinary configuration resources without wildcard merging or workload execution', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch', '', '# Job Templates, after their dependencies', '- name: Import job templates after their persistent credential dependencies', '  ansible.builtin.include_role:', '    name: infra.aap_configuration.controller_job_templates'];
    if (stage === 2 || state.step.baseFocus === 'rhel') return ['# 02-infra-config.yml · excerpt', '- name: "Configure DNS, certificate, and nginx reverse proxy"', '  hosts: hypervisor', '  become: true', '  gather_facts: false'];
    if (stage === 3) return ['# 03-aap-install.yml · excerpt', '- name: Run AAP installer', '  ansible.builtin.command:', '    cmd: ansible-playbook -i inventory ansible.containerized_installer.install', '    chdir: "{{ installer_extract_dir }}/{{ installer_dir_name }}"', '  async: 7200', '  poll: 30'];
    return ['# 04-aap-config.yml · excerpt', '- name: Configure new AAP instance (config-as-code)', '  hosts: localhost', '  connection: local', '  gather_facts: false', '', '  # Verified target API', '  # aap_validate_certs: true'];
  }
  const api = { sourceRevision, sourceRoot, chapters, steps, stateAt, configurationLines, executionLines };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AapCacStory = api;
})(typeof window !== 'undefined' ? window : globalThis);
