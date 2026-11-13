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
    { id: 'infrastructure', chapter: 'deployment', title: 'Prepare OS for AAP installation', description: 'DNS, TLS certificates and nginx connect that same guest to its reserved address. The VM is ready for AAP installation.', stage: 2, job: '02 · Prepare OS for AAP installation', status: 'OS prepared for AAP installation', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['02-infra-config.yml'] },
    { id: 'installation', chapter: 'deployment', title: '03 / Install AAP inside the VM.', description: 'The platform is installed in the new guest. A second AAP now exists; its automation catalogue comes next.', stage: 3, job: '03 · Install AAP', status: 'AAP installed', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['03-aap-install.yml'] },
    { id: 'base-aap', chapter: 'deployment', title: 'AAP configuration', description: 'Apply AAP Logging Config v1 and AAP EDA Config v1. RHEL configuration is retained; shared automation objects come next.', stage: 4, baseFocus: 'aap', job: 'Apply AAP configuration', status: 'AAP configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['04-aap-config.yml'] },
    { id: 'base', chapter: 'deployment', title: 'AAP content', description: 'Import the shared inventories, projects, credentials and Job Templates. The initial RHEL configuration, AAP settings and base automation content are now applied.', stage: 4, baseFocus: 'content', job: 'Import base AAP content', status: 'Base configuration applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['04-aap-config.yml'] },
    { id: 'infra-change', chapter: 'git-change', title: 'Apply infrastructure configuration.', description: 'CaC updates the RHEL infrastructure configuration: Certificate config becomes purple v2, while Firewall Config stays blue v1.', stage: 4, job: 'Apply infrastructure configuration', status: 'Certificate v2 applied; firewall v1 unchanged', routes: ['flow-config', 'flow-code', 'flow-apply'], actor: ['Infrastructure author', 'Updates Certificate config to v2 and retains Firewall Config v1.'], sources: ['02-infra-config.yml', 'deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'git-change', chapter: 'git-change', title: 'New requirements? Change the YAML.', description: 'Your team updates AAP Logging Config v1 to v2 in CaC. The original AAP applies the settings change; AAP EDA Config v1 and the base automation objects stay unchanged. Additional AAP objects come next.', stage: 4, job: 'Apply configuration', status: 'AAP Logging Config v2 applied; AAP EDA Config v1 unchanged', routes: ['flow-config', 'flow-code', 'flow-apply'], actor: ['Configuration author', 'Updates AAP Logging Config to v2. AAP EDA Config v1 and the base objects are retained.'], sources: ['04-aap-config.yml'] },
    { id: 'project', chapter: 'project', title: 'Turn definitions into more automation.', description: 'A configuration Job Template on the original AAP combines the private YAML with the public playbooks. Additional objects appear on the receiving AAP.', stage: 4, job: 'Deploy objects', status: 'Project objects applied', routes: ['flow-config', 'flow-code', 'flow-apply'], sources: ['deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
    { id: 'manual', chapter: 'manual', title: 'Sometimes, changes happen in the UI.', description: 'An operator adds an inventory, project and credential directly on the receiving AAP. They exist there now, but their definitions are not in Git yet.', stage: 4, job: 'Ready to scan configuration', status: 'Manual objects added', routes: [], actor: ['Sysadmin · incident response', 'Responds to an outage and creates objects directly in the receiving AAP.'], sources: ['capture-aap-cac.yml'] },
    { id: 'capture', chapter: 'capture', title: 'Bring those changes back into Git.', description: 'A configuration scan Job Template on the original AAP reads the added objects and brings their definitions into the encrypted CaC. The next setup can use them too.', stage: 4, job: 'Scan AAP configuration', status: 'Added definitions recorded in Git', routes: ['flow-scan', 'flow-return'], sources: ['capture-aap-cac.yml', 'docs/cac-reconciliation.md'] },
    { id: 'next-aap', chapter: 'rebuild', title: 'Ready for another AAP.', description: 'The complete configuration is now in Git. Prepare the next destination, then deploy another AAP from those saved definitions.', stage: 4, job: 'Ready for the next deployment', status: 'Configuration ready to reuse', routes: [], sources: ['01-linux-vm-setup.yml'] },
    { id: 'rebuild', chapter: 'rebuild', title: 'Deploy the complete configuration again.', description: 'The original AAP creates another AAP from the configuration now kept in Git: base definitions, Git changes and captured manual additions, with AAP Logging Config v2, AAP EDA Config v1, Certificate config v2 and Firewall Config v1.', stage: 4, job: 'Rebuild from Git', status: 'Another AAP restored from Git', routes: ['flow-config', 'flow-code', 'flow-rebuild'], sources: ['01-linux-vm-setup.yml', '02-infra-config.yml', '03-aap-install.yml', '04-aap-config.yml', 'deploy-cac-project.yml', 'tasks/cac-resource-definitions.yml'] },
  ];
  const stepPositions = Object.fromEntries(steps.map((step, position) => [step.id, position]));
  const chapters = [
    ['separation', 'Data & code'], ['deployment', 'A new AAP'],
    ['git-change', 'Change in Git'], ['project', 'Apply objects'],
    ['manual', 'Change in AAP'], ['capture', 'Back to Git'], ['rebuild', 'Deploy again'],
  ].map(([id, title]) => ({ id, title, index: steps.findIndex(step => step.chapter === id) }));
  function stateAt(index) {
    if (!Number.isInteger(index)) throw new TypeError('Step index must be an integer.');
    const position = Math.max(0, Math.min(steps.length - 1, index));
    const step = steps[position];
    const rhelConfigurationApplied = step.stage >= 2;
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
    const flowOrigin = rebuilding ? 'mixed' : position >= stepPositions.manual ? 'manual' : position >= stepPositions['infra-change'] ? 'git' : 'base';
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
  // Presentation-only ciphertext: synthetic hex, with no key or decryptable payload.
  // Scope and the mixed encrypted/decrypted view: ../README.md#code-and-data.
  const illustrativeVaultHex = [
    '65643332636439633532376631383636656538653761346339333363373937663838613762636533373061',
    '31613831326138393435306432303163386361306630376466383336643162383964373565663162653365',
    '30346230353866313862363334653364613864323734616234353265626133643765653430386634313461',
  ];
  function encryptedExample(key) {
    return [`${key}: !vault |`, '  $ANSIBLE_VAULT;1.1;AES256', ...illustrativeVaultHex.map(line => `  ${line}`)];
  }
  function configurationLines(state) {
    const lines = [];
    const id = state.step.id;
    const replaying = state.rebuilding;
    function append(section, texts, options = {}) {
      const { origin = 'base', active = false, focus = active, added = false } = options;
      for (const text of texts) lines.push({ text, origin, active, section, focus, added, illustrative: true });
    }
    append('preamble', [
      '# Illustrative private YAML · encrypted inputs and decrypted object examples',
      '# All !vault blocks below are synthetic, non-decryptable demonstration data.',
      '# Input groups are explanatory examples, not a ready-to-run inventory.',
    ]);
    append('vm', [
      '', '# VM creation · illustrative encrypted inputs',
      'vm_name: "{{ reserved_vm_name }}"',
      'vm_network: "{{ guest_network }}"',
      'aap_golden_image_path: "{{ verified_golden_image_path }}"',
      ...encryptedExample('vault_ansible_password'),
    ], { active: replaying || id === 'vm', focus: replaying || ['separation', 'vm', 'next-aap'].includes(id) });

    const certificate = state.desiredInfrastructure.find(config => config.id === 'certificate');
    const rhelActive = replaying || id === 'infrastructure';
    append('certificate', [
      '', `# RHEL infrastructure · ${certificate.name}`,
      `aap_upstream_hostname: ${certificate.version === 1 ? '<automation-service-name>' : '<updated-automation-service-name>'}`,
      '# Encrypted certificate settings; this does not store a TLS private key.',
      ...encryptedExample('certificate_config_encrypted'),
    ], { origin: certificate.origin, active: rhelActive || id === 'infra-change' });
    const firewall = state.desiredInfrastructure.find(config => config.id === 'firewall');
    append('firewall', [
      '', `# ${firewall.name} · illustrative encrypted rule inputs`,
      ...encryptedExample('firewall_rule_encrypted'),
      '# Saved job inputs; importing a definition does not execute it.',
      'firewall_job_inputs:',
      `  - name: ${firewall.template}`,
      '    extra_vars:',
      `      config_revision: v${firewall.version}`,
    ], { origin: firewall.origin, active: rhelActive });

    append('installation', [
      '', '# AAP installation · illustrative encrypted credentials',
      'installer_extract_dir: <installer-working-directory>',
      'installer_dir_name: <selected-installer-directory>',
      ...encryptedExample('installer_credentials_encrypted'),
    ], { active: replaying || id === 'installation' });
    const logging = state.desiredConfiguration.find(config => config.id === 'logging');
    const aapActive = replaying || id === 'base-aap';
    append('logging', [
      '', `# ${logging.name}`,
      'controller_settings_base:',
      '  settings:',
      `    LOG_AGGREGATOR_ACTION_QUEUE_SIZE: ${logging.version === 1 ? 10000 : 20000}`,
    ], { origin: logging.origin, active: aapActive || id === 'git-change' });
    append('eda', [
      '# AAP EDA Config v1 · illustrative configuration excerpt',
      'eda_decision_environments_base:',
      '  - name: Event runtime',
      '    image_url: <decision-environment-image>',
      'eda_rulebook_activations_base:',
      '  - name: Event policy',
      '    decision_environment: Event runtime',
      '    log_level: info',
    ], { active: aapActive });
    append('aap-secrets', [
      '# AAP configuration · illustrative encrypted API and service inputs',
      ...encryptedExample('aap_secrets_encrypted'),
    ], { active: aapActive });

    const fields = [
      ['Inventories', 'controller_inventories', 'inventories'],
      ['Projects', 'controller_projects', 'projects'],
      ['Credentials', 'controller_credentials', 'credentials'],
      ['Job Templates', 'controller_templates', 'job-templates'],
    ];
    for (const [type, key, section] of fields) {
      append(section, ['', `${key}:`]);
      for (const object of state.configObjects.filter(item => item.type === type)) {
        const added = object.origin === 'manual';
        const active = replaying || id === 'base' && object.origin === 'base'
          || id === 'project' && object.origin === 'git' || id === 'capture' && added;
        const texts = [`  - name: ${object.name}`];
        if (type === 'Projects') texts.push('    scm_url: <automation-repository>');
        append(section, texts, { origin: object.origin, added, active });
      }
      if (type === 'Inventories') append('inventory-sources', [
        'controller_inventory_sources:',
        '  - name: VMWare Inventory source',
        '    inventory: VMWare Inventory',
        '    source: scm',
      ], { active: replaying || id === 'base' });
    }
    append('manual-note', [
      '', '# Manual additions enter this Git file only after the accepted capture.',
      '# API access uses verified HTTPS',
    ], { focus: id === 'manual' });
    return lines;
  }
  // One continuous presentation file combines exact excerpts from separate sources.
  // The real playbooks remain separate; see ../README.md#code-and-data.
  const executionSections = [
    { id: 'vm', source: '01-linux-vm-setup.yml', lines: [
      '# 01-linux-vm-setup.yml · excerpt',
      '- name: Create a test VM only after shared name reservation and pinned rebuild preflight',
      '  hosts: hypervisor', '  become: true', '  gather_facts: false',
    ] },
    { id: 'infrastructure', source: '02-infra-config.yml', lines: [
      '', '# 02-infra-config.yml · excerpt',
      '- name: "Configure DNS, certificate, and nginx reverse proxy"',
      '  hosts: hypervisor', '  become: true', '  gather_facts: false',
    ] },
    { id: 'installation', source: '03-aap-install.yml', lines: [
      '', '# 03-aap-install.yml · excerpt', '- name: Run AAP installer',
      '  ansible.builtin.command:',
      '    cmd: ansible-playbook -i inventory ansible.containerized_installer.install',
      '    chdir: "{{ installer_extract_dir }}/{{ installer_dir_name }}"',
      '  async: 7200', '  poll: 30',
    ] },
    { id: 'aap-settings', source: '04-aap-config.yml', lines: [
      '', '# Platform settings · 04-aap-config.yml',
      '- name: Apply shared AAP configuration', '  ansible.builtin.include_role:',
      '    name: infra.aap_configuration.dispatch', '  vars:',
      '    dispatch_include_wildcard_vars: false',
    ] },
    { id: 'base-content', source: '04-aap-config.yml', lines: [
      '', '# 04-aap-config.yml · excerpt',
      '- name: Configure new AAP instance (config-as-code)',
      '  hosts: localhost', '  connection: local', '  gather_facts: false',
      '', '  # Verified target API', '  # aap_validate_certs: true',
    ] },
    { id: 'project-resources', source: 'tasks/cac-resource-definitions.yml', lines: [
      '', '# Inventories, projects and credentials · tasks/cac-resource-definitions.yml',
      '- name: Import ordinary configuration resources without wildcard merging or workload execution',
      '  ansible.builtin.include_role:', '    name: infra.aap_configuration.dispatch',
    ] },
    { id: 'job-templates', source: 'tasks/cac-resource-definitions.yml', lines: [
      '', '# Job Templates, after their dependencies · tasks/cac-resource-definitions.yml',
      '- name: Import job templates after their persistent credential dependencies',
      '  ansible.builtin.include_role:', '    name: infra.aap_configuration.controller_job_templates',
    ] },
    { id: 'capture-implementation', source: 'capture-aap-cac.yml', lines: [
      '', '# capture-aap-cac.yml · excerpt',
      '- name: Extract and compare through protected Vault API and Git inputs',
      '  aap_cac_capture:', '    scope: "{{ aap_cac_capture_scope }}"',
    ] },
    { id: 'capture-inputs', source: 'capture-aap-cac.yml', illustrative: true, lines: [
      '', '# Accepted update · illustrative job inputs, not executable role lines',
      'aap_cac_capture_mode: update', 'aap_cac_capture_commit: true', 'aap_cac_capture_push: true',
      '# Implementation: capture-aap-cac.yml',
    ] },
  ];
  const executionFocus = {
    separation: ['project-resources', 'job-templates'],
    vm: ['vm'], infrastructure: ['infrastructure'], installation: ['installation'],
    'base-aap': ['aap-settings'], base: ['base-content'],
    project: ['project-resources', 'job-templates'], 'git-change': ['aap-settings'],
    'infra-change': ['infrastructure', 'job-templates'],
    manual: ['capture-implementation'], capture: ['capture-implementation', 'capture-inputs'],
    'next-aap': ['vm'],
    rebuild: ['vm', 'infrastructure', 'installation', 'aap-settings', 'base-content', 'project-resources', 'job-templates'],
  };
  function executionLines(state) {
    const focusedSections = executionFocus[state.step.id];
    return executionSections.flatMap(section => {
      const focus = focusedSections.includes(section.id);
      const active = focus && state.step.routes.includes('flow-code');
      const origin = active ? (state.rebuilding ? 'git' : state.flowOrigin) : 'base';
      return section.lines.map(text => ({
        text, origin, active, section: section.id, focus,
        source: section.source, sources: [section.source], illustrative: Boolean(section.illustrative),
      }));
    });
  }
  const api = { sourceRevision, sourceRoot, chapters, steps, stateAt, configurationLines, executionLines };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.AapCacStory = api;
})(typeof window !== 'undefined' ? window : globalThis);
