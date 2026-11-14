'use strict';
// Exercise real presentation scripts without browser dependencies. Scope: ../README.md#verification.
const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const checkoutDemo = path.resolve(__dirname, '..');
const repository = path.resolve(checkoutDemo, '..');
// Live verification supplies downloaded assets; code citations still use this checkout.
const demo = process.env.AAP_CAC_DEMO_DIR ? path.resolve(process.env.AAP_CAC_DEMO_DIR) : checkoutDemo;
const story = require(path.join(demo, 'src/scenario.js'));
const source = name => readFileSync(path.join(demo, name), 'utf8');
const futureRoutes = ['flow-apply', 'flow-scan', 'flow-return', 'flow-rebuild'];

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.handlers = {};
    this.scrollRequests = [];
    this.offsetTop = 0;
    this.offsetHeight = 0;
    this.hidden = false;
    this.disabled = false;
    this.classes = new Set();
    this.classList = {
      toggle: (name, active) => active ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  set className(value) { this.classes = new Set(value.split(/\s+/).filter(Boolean)); }
  get className() { return [...this.classes].join(' '); }
  set textContent(value) { this.ownText = String(value); this.children = []; }
  get textContent() { return (this.ownText || '') + this.children.map(child => child.textContent).join(''); }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'class') this.className = value;
    if (name === 'hidden') this.hidden = true;
    if (name === 'disabled') this.disabled = true;
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value);
  }
  removeAttribute(name) {
    delete this.attributes[name];
    if (name === 'hidden') this.hidden = false;
    if (name === 'disabled') this.disabled = false;
  }
  append(...nodes) {
    nodes.forEach(node => {
      node.parentElement = this;
      // Deterministic offsets verify scroll selection without simulating browser geometry.
      if (['config-lines', 'code-lines'].includes(this.attributes.id)) node.offsetTop = this.offsetTop + this.children.length * 24;
      this.children.push(node);
    });
  }
  replaceChildren(...nodes) { this.children = []; this.ownText = ''; this.append(...nodes); }
  addEventListener(name, callback) { (this.handlers[name] ||= []).push(callback); }
  scrollIntoView(options) { this.scrollRequests.push(options); }
  click() { if (!this.disabled) (this.handlers.click || []).forEach(callback => callback({ target: this })); }
  closest() {
    for (let node = this; node; node = node.parentElement) {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(node.tagName) || node.attributes.contenteditable === 'true') return node;
    }
    return null;
  }
}
function descendants(node) { return node.children.flatMap(child => [child, ...descendants(child)]); }
function withClass(node, name) { return descendants(node).filter(child => child.classList.contains(name)); }
function attributes(element, text) {
  const pattern = /([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
  for (const match of text.matchAll(pattern)) element.setAttribute(match[1], match[2] ?? match[3] ?? match[4] ?? '');
  return element;
}
function htmlRegion(html, id) {
  const opening = html.match(new RegExp(`<([a-z][\\w:-]*)\\b[^>]*\\bid="${id}"[^>]*>`, 'i'));
  assert.ok(opening, `Missing actual HTML region ${id}`);
  let depth = 0;
  for (const tag of html.slice(opening.index).matchAll(new RegExp(`<\\/?${opening[1]}\\b[^>]*>`, 'gi'))) {
    depth += tag[0].startsWith('</') ? -1 : 1;
    if (depth === 0) return html.slice(opening.index, opening.index + tag.index + tag[0].length);
  }
  assert.fail(`${id} has no matching closing tag`);
}
function browser(hash = '') {
  const html = source('index.html');
  const nodes = {};
  for (const match of html.matchAll(/<([a-z][\w:-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
    assert.equal(nodes[match[3]], undefined, `Duplicate HTML ID ${match[3]}`);
    nodes[match[3]] = attributes(new Element(match[1]), match[2]);
  }
  for (const id of ['config-lines', 'code-lines']) {
    const viewport = new Element('pre');
    viewport.append(nodes[id]);
    nodes[id].offsetTop = 120;
  }
  const document = {
    handlers: {},
    getElementById(id) { assert.ok(nodes[id], `Missing actual HTML ID ${id}`); return nodes[id]; },
    createElement: tag => new Element(tag),
    addEventListener(name, callback) { this.handlers[name] = callback; },
  };
  const location = { hash };
  const context = vm.createContext({ document, location, history: { replaceState(unusedState, unusedTitle, next) { location.hash = next; } } });
  context.window = context;
  context.addEventListener = (name, callback) => { context[name] = callback; };
  vm.runInContext(source('src/scenario.js'), context, { filename: 'scenario.js' });
  vm.runInContext(source('src/app.js'), context, { filename: 'app.js' });
  return {
    nodes, context,
    chapter(id) { const button = nodes['chapter-list'].children.find(item => item.dataset.chapter === id); assert.ok(button, `Missing chapter ${id}`); button.click(); },
    hash(next) { location.hash = next; context.hashchange(); },
    key(key, extra = {}) { const event = { key, target: new Element(), preventDefault() { this.prevented = true; }, ...extra }; document.handlers.keydown(event); return event; },
  };
}
const automationItems = node => withClass(node, 'object-group').flatMap(group => withClass(group, 'object-item'));
function objectNames(node) {
  const groups = withClass(node, 'object-group');
  const names = groups.length ? groups.flatMap(group => withClass(group, 'object-name')) : withClass(node, 'object-name');
  return names.map(item => item.textContent);
}
const manualItems = node => withClass(node, 'object-item').filter(item => item.dataset.origin === 'manual');

test('the seven chapters cover deployment, capture and replay with existing source links', () => {
  assert.equal(story.chapters.length, 7);
  assert.equal(story.steps.length, 13);
  assert.deepEqual(story.steps.map(step => step.id), ['separation', 'vm', 'infrastructure', 'installation', 'base-aap', 'base', 'infra-change', 'git-change', 'project', 'manual', 'capture', 'next-aap', 'rebuild']);
  assert.deepEqual(story.chapters.map(chapter => chapter.id), ['separation', 'deployment', 'git-change', 'project', 'manual', 'capture', 'rebuild']);
  assert.ok(story.steps.every(step => step.id !== 'base-rhel'), 'OS preparation already applies RHEL configuration; no duplicate apply stop remains');
  assert.deepEqual(story.steps.slice(1, 6).map(step => step.stage), [1, 2, 3, 4, 4]);
  assert.ok(story.steps.slice(1, 6).every(step => step.chapter === 'deployment'));
  assert.equal(new Set(story.steps.map(step => step.id)).size, 13);
  assert.equal(story.steps.find(step => step.id === 'infra-change').chapter, 'git-change');
  assert.equal(story.steps.at(-1).id, 'rebuild');
  assert.deepEqual(story.stateAt(0).sourceObjects.map(object => object.name), [
    'VMWare Inventory', 'AAP Config-as-Code Git', 'Server access key', 'AAP Config-as-Code jobs',
  ], 'The source uses the requested names for its base inventory, project, credential and jobs');
  const project = story.stateAt(story.steps.findIndex(step => step.id === 'project'));
  assert.deepEqual(project.targetObjects.filter(object => object.origin === 'git').map(object => object.name), [
    'Satellite Inventory', 'Application automation playbooks', 'Application auth token', 'Deploy application', 'Regional servers', 'Regional automation',
  ], 'Project imports preserve the requested inventory, project and credential names');
  const configuration = story.configurationLines(project).map(line => line.text).join('\n');
  assert.match(configuration, /name: VMWare Inventory source/);
  assert.match(configuration, /inventory: VMWare Inventory(?:\n|$)/);
  const initialConfiguration = story.configurationLines(story.stateAt(0)).map(line => line.text).join('\n');
  for (const name of ['Regional servers', 'Regional automation']) assert.ok(initialConfiguration.includes(name), `${name}: project definition is already in Git`);

  assert.match(story.sourceRevision, /^[a-f0-9]{40}$/);
  const publicSections = ['vm', 'certificate', 'firewall', 'installation', 'aap-settings', 'base-content', 'project-resources', 'job-templates', 'capture-implementation', 'capture-inputs'];
  const publicEntries = story.executionLines(story.stateAt(0));
  const completePublicText = publicEntries.map(line => line.text).join('\n');
  const sectionText = section => publicEntries.filter(line => line.section === section).map(line => line.text).join('\n');
  const certificate = sectionText('certificate');
  assert.match(certificate, /ansible\.builtin\.command:/);
  assert.match(certificate, /certbot certonly --nginx/);
  assert.match(certificate, /-d \{\{ aap_test_subdomain \}\}\.\{\{ vault_domain \}\}/);
  assert.match(certificate, /creates:.*fullchain\.pem/);
  const firewall = sectionText('firewall');
  assert.match(firewall, /ansible\.builtin\.include_role:/);
  assert.match(firewall, /name: redhat\.rhel_system_roles\.firewall/);
  assert.match(firewall, /rich_rule:.*\{\{ aap_management_native_plan\.rich_rule \}\}/);
  for (const setting of ['state: enabled', 'runtime: true', 'permanent: true', 'no_log: true']) assert.ok(firewall.includes(setting));
  for (const [section, reference] of [['certificate', '02-infra-config.yml'], ['firewall', 'tasks/aap-hypervisor-access.yml']]) {
    assert.ok(publicEntries.filter(line => line.section === section).every(line => line.source === reference), `${section}: the actual implementation source is cited`);
  }
  const baseContent = sectionText('base-content');
  assert.match(baseContent, /#.*localhost/i);
  assert.match(baseContent, /#.*(?:execution environment|job EE)/i);
  assert.match(baseContent, /#.*aap_hostname/);

  const sourceTexts = new Map();
  const readReference = reference => {
    assert.ok(existsSync(path.resolve(repository, reference)), reference);
    if (!sourceTexts.has(reference)) sourceTexts.set(reference, readFileSync(path.resolve(repository, reference), 'utf8'));
    return sourceTexts.get(reference);
  };
  for (const [index, step] of story.steps.entries()) {
    for (const reference of step.sources) readReference(reference);
    const entries = story.executionLines(story.stateAt(index));
    assert.equal(entries.map(line => line.text).join('\n'), completePublicText, `${step.id}: the public pane retains the complete file`);
    assert.deepEqual([...new Set(entries.map(line => line.section))], publicSections, `${step.id}: all public workflow sections remain present`);
    for (const entry of entries) {
      assert.equal(typeof entry.text, 'string');
      assert.equal(typeof entry.active, 'boolean');
      assert.equal(typeof entry.focus, 'boolean');
      assert.equal(entry.illustrative, entry.section === 'capture-inputs');
      assert.ok(Array.isArray(entry.sources) && entry.sources.length, `${entry.section}: pinned source metadata`);
      assert.equal(entry.source, entry.sources[0]);
      const code = entry.sources.map(readReference).join('\n');
      if (!entry.text.trim() || entry.text.trimStart().startsWith('#')) continue;
      if (entry.illustrative) {
        const match = entry.text.match(/^(aap_cac_capture_(?:scope|mode|commit|push)):\s+(.+)$/);
        assert.ok(match, `Unknown illustrative capture input: ${entry.text}`);
        assert.ok(code.includes(match[1]), `Capture implementation does not accept ${match[1]}`);
      } else {
        const actualLines = new Set(code.split('\n').map(line => line.trim()));
        assert.ok(actualLines.has(entry.text.trim()), `Unmapped ${entry.section} execution excerpt: ${entry.text}`);
      }
    }
    const inputs = entries.filter(line => line.section === 'capture-inputs').map(line => line.text);
    for (const input of ['aap_cac_capture_mode: update', 'aap_cac_capture_commit: true', 'aap_cac_capture_push: true']) assert.ok(inputs.includes(input));
  }

});

test('the actual HTML hides future objects before scripts run and uses local assets', () => {
  const html = source('index.html');
  for (const id of ['source-infrastructure-title', 'target-infrastructure-title', 'successor-infrastructure-title', 'target-rhel-detail', 'successor-rhel-detail']) {
    assert.doesNotMatch(html, new RegExp(`\\bid="${id}"`), `${id}: removed caption does not remain in the page`);
  }
  const opening = id => { const match = html.match(new RegExp(`<[^>]*\\bid="${id}"[^>]*>`)); assert.ok(match, id); return match[0]; };
  assert.match(opening('target-card'), /\bhidden\b/);
  assert.match(opening('target-card'), /aria-hidden="true"/);
  assert.match(opening('successor-card'), /\bhidden\b/);
  assert.match(opening('successor-card'), /aria-hidden="true"/);
  assert.match(opening('target-infrastructure-panel'), /\bhidden\b/);
  assert.doesNotMatch(opening('source-card'), /\bhidden\b/);
  for (const route of futureRoutes) assert.match(opening(route), /\bhidden\b/);
  for (const route of ['flow-config', 'flow-code']) assert.doesNotMatch(opening(route), /\bhidden\b/);
  for (const match of html.matchAll(/(?:href|src)="([^"#]+\.(?:css|js|svg|png))"/g)) assert.ok(existsSync(path.join(demo, match[1])), match[1]);
  assert.match(source('src/styles.css'), /\[hidden\][\s\S]{0,100}display\s*:\s*none/);
});

test('Next and Previous apply RHEL during OS preparation, then AAP settings and base content', () => {
  const page = browser();
  const { nodes } = page;
  const sourceNames = objectNames(nodes['source-objects']);
  assert.equal(nodes['target-card'].hidden, true);
  assert.equal(nodes['target-placeholder'].hidden, false);
  assert.equal(nodes['previous'].disabled, true);
  assert.equal(nodes['stage-list'], undefined, 'The redundant stage section is deleted');
  assert.doesNotMatch(source('index.html'), /AAP DEPLOYMENT|<button\b[^>]*data-stage=/);
  const stops = [
    ['vm', 1, false, false, false],
    ['infrastructure', 2, true, false, false],
    ['installation', 3, true, false, false],
    ['base-aap', 4, true, true, false],
    ['base', 4, true, true, true],
  ];
  const check = ([id, stage, rhel, settings, content]) => {
    const state = story.stateAt(story.steps.findIndex(step => step.id === id));
    assert.equal(state.rhelConfigurationApplied, rhel, `${id}: RHEL apply state`);
    assert.equal(state.aapConfigurationApplied, settings, `${id}: AAP settings apply state`);
    assert.equal(state.baseContentApplied, content, `${id}: base content apply state`);
    assert.equal(nodes['target-card'].dataset.stage, String(stage));
    assert.equal(nodes['scene-title'].textContent, state.step.title);
    assert.equal(nodes['target-card'].hidden, false);
    assert.equal(nodes['target-placeholder'].hidden, true);
    assert.equal(nodes['target-card'].attributes['aria-hidden'], 'false');
    assert.equal(nodes['target-title'].textContent, stage < 3 ? 'New RHEL VM' : 'New AAP');
    assert.equal(nodes['target-objects'].hidden, !content, `${id}: content visibility`);
    assert.equal(nodes['target-configuration-panel'].hidden, !settings, `${id}: settings visibility`);
    assert.deepEqual(objectNames(nodes['target-objects']).sort(), content ? [...sourceNames].sort() : [], `${id}: base objects`);
    assert.deepEqual(objectNames(nodes['target-configuration']), settings ? ['AAP Logging Config v1', 'AAP EDA Config v1'] : [], `${id}: AAP settings`);
    assert.deepEqual(objectNames(nodes['target-infrastructure']), stage >= 2 ? ['Certificate config v1', 'Firewall Config v1'] : [], `${id}: canonical RHEL profiles`);
    assert.deepEqual(objectNames(nodes['source-objects']), sourceNames, `${id}: original AAP is preserved`);
  };
  for (const stop of stops) {
    nodes.next.click();
    check(stop);
  }
  for (const stop of stops.slice(0, -1).reverse()) {
    nodes.previous.click();
    check(stop);
  }
});

test('the source job reads both repositories and applies project objects', () => {
  const page = browser();
  page.chapter('project');
  const { nodes } = page;
  assert.equal(nodes['job-label'].textContent, 'Deploy objects');
  assert.equal(nodes['source-card'].classList.contains('phase-job'), true);
  assert.equal(nodes['config-card'].classList.contains('active'), true);
  assert.equal(nodes['code-card'].classList.contains('active'), true);
  assert.equal(objectNames(nodes['source-objects']).length, 4);
  assert.equal(objectNames(nodes['target-objects']).length, 10);
  assert.ok(objectNames(nodes['target-objects']).includes('Satellite Inventory'));
  assert.ok(objectNames(nodes['target-objects']).includes('Deploy application'));
  assert.equal(withClass(nodes['target-objects'], 'object-item').filter(item => item.dataset.origin === 'git').length, 6);
  for (const name of ['Regional servers', 'Regional automation']) assert.ok(objectNames(nodes['target-objects']).includes(name), `${name}: deployed with the project objects`);
  assert.equal(nodes['flow-apply'].hidden, false);
});

test('purple Git changes apply RHEL, AAP settings and additional objects in layer order', () => {
  const page = browser('#base');
  const { nodes } = page;
  const original = objectNames(nodes['source-objects']);
  const baseObjects = objectNames(nodes['target-objects']);
  assert.equal(baseObjects.length, 4);
  for (const [id, logging, objectCount] of [
    ['infra-change', 'AAP Logging Config v1', 4],
    ['git-change', 'AAP Logging Config v2', 4],
    ['project', 'AAP Logging Config v2', 10],
  ]) {
    nodes.next.click();
    assert.equal(nodes['scene-title'].textContent, story.steps.find(step => step.id === id).title);
    assert.deepEqual(objectNames(nodes['target-infrastructure']), ['Certificate config v2', 'Firewall Config v1'], `${id}: RHEL changes land first`);
    assert.deepEqual(objectNames(nodes['target-configuration']), [logging, 'AAP EDA Config v1'], `${id}: AAP settings change second`);
    assert.equal(objectNames(nodes['target-objects']).length, objectCount, `${id}: additional objects land last`);
    if (objectCount === 4) assert.deepEqual(objectNames(nodes['target-objects']), baseObjects);
    for (const name of ['Regional servers', 'Regional automation']) {
      assert.equal(objectNames(nodes['target-objects']).includes(name), id === 'project', `${id}: ${name} is added only at the objects stop`);
    }
    for (const route of ['flow-config', 'flow-code', 'flow-apply']) assert.equal(nodes[route].dataset.origin, 'git', `${id}: purple apply route`);
    assert.deepEqual(objectNames(nodes['source-objects']), original, `${id}: original AAP objects are preserved`);
  }
  page.hash('#git-change');
  assert.equal(withClass(nodes['config-lines'], 'line-added').length, 0, 'The settings edit does not introduce new inventory or project definitions');
  const highlighted = withClass(nodes['config-lines'], 'line-active').map(line => line.textContent);
  assert.ok(highlighted.some(line => line.includes('AAP Logging Config v2')));
  for (const name of ['Regional servers', 'Regional automation']) {
    assert.ok(nodes['config-lines'].textContent.includes(name));
    assert.ok(!highlighted.some(line => line.includes(name)), `${name}: not part of the settings update`);
  }
  assert.match(nodes['code-lines'].textContent, /Import ordinary configuration resources/, 'The full public file retains imports at the settings stop');
  assert.doesNotMatch(withClass(nodes['code-lines'], 'line-active').map(line => line.textContent).join('\n'), /Import ordinary configuration resources/, 'Only settings application is highlighted at this stop');
  assert.equal(nodes.actor.hidden, false);
  assert.equal(nodes['actor-title'].textContent, 'Configuration author');
});


test('manual objects exist on the target but remain absent from CaC until capture', () => {
  const page = browser('#manual');
  const { nodes } = page;
  assert.equal(manualItems(nodes['target-objects']).length, 3);
  for (const name of ['Emergency servers', 'Quick-fix automation', 'Temporary access']) {
    assert.ok(objectNames(nodes['target-objects']).includes(name));
    assert.ok(!nodes['config-lines'].textContent.includes(name));
  }
  assert.ok(manualItems(nodes['target-objects']).every(item => item.dataset.inGit === 'false'));
  assert.equal(nodes.feedback, undefined, 'The removed bottom-left summary has no hidden DOM replacement');
  assert.equal(nodes['flow-apply'].hidden, true);
  page.chapter('capture');
  for (const item of manualItems(nodes['target-objects'])) {
    const name = withClass(item, 'object-name')[0].textContent;
    assert.ok(nodes['config-lines'].textContent.includes(name));
    assert.equal(item.dataset.inGit, 'true');
    assert.equal(item.dataset.origin, 'manual');
    assert.equal(item.textContent, name, 'Capture preserves colour origin without adding visible badges');
  }
  assert.equal(nodes['flow-scan'].hidden, false);
  assert.equal(nodes['flow-return'].hidden, false);
  assert.equal(nodes['flow-apply'].hidden, true);
  assert.equal(nodes['job-label'].textContent, 'Scan AAP configuration');
});

test('backwards navigation and restart reverse capture, manual additions and settings updates', () => {
  const { nodes } = browser('#capture');
  nodes.previous.click();
  assert.equal(manualItems(nodes['target-objects']).length, 3);
  assert.ok(manualItems(nodes['target-objects']).every(item => item.dataset.inGit === 'false'), 'Reversing capture restores unsaved manual objects');
  assert.ok(!nodes['config-lines'].textContent.includes('Emergency servers'));
  nodes.previous.click();
  assert.equal(manualItems(nodes['target-objects']).length, 0);
  assert.ok(nodes['config-lines'].textContent.includes('Regional servers'));
  nodes.previous.click();
  assert.equal(objectNames(nodes['target-objects']).length, 4, 'Backing up from project removes its additional objects');
  assert.deepEqual(objectNames(nodes['target-configuration']), ['AAP Logging Config v2', 'AAP EDA Config v1']);
  assert.deepEqual(objectNames(nodes['target-infrastructure']), ['Certificate config v2', 'Firewall Config v1']);
  nodes.previous.click();
  assert.equal(objectNames(nodes['target-objects']).length, 4, 'The RHEL update precedes additional project objects');
  assert.deepEqual(objectNames(nodes['target-configuration']), ['AAP Logging Config v1', 'AAP EDA Config v1'], 'Backing up before the logging update restores its v1 settings');
  assert.deepEqual(objectNames(nodes['target-infrastructure']), ['Certificate config v2', 'Firewall Config v1'], 'The preceding RHEL update is retained');
  nodes.previous.click();
  assert.ok(!objectNames(nodes['target-objects']).includes('Regional servers'), 'Base AAP does not yet contain the additional project inventory');
  assert.deepEqual(objectNames(nodes['target-infrastructure']), ['Certificate config v1', 'Firewall Config v1'], 'Backing up before the RHEL update restores its v1 settings');
  assert.ok(nodes['config-lines'].textContent.includes('Regional servers'), 'Its desired definition remains in Git before deployment');
  nodes.restart.click();
  assert.equal(nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  assert.equal(nodes['target-card'].hidden, true);
  assert.equal(nodes['target-placeholder'].hidden, false);
  assert.equal(nodes.actor.hidden, true);
  for (const route of futureRoutes) assert.equal(nodes[route].hidden, true, route);
  for (const route of ['flow-config', 'flow-code']) {
    assert.equal(nodes[route].hidden, false, route);
    assert.equal(nodes[route].classList.contains('active'), false, route);
  }
});

test('next, previous and keyboard navigation remain bounded and respect text editing', () => {
  const page = browser();
  const { nodes } = page;
  for (let index = 0; index < story.steps.length; index++) {
    assert.equal(nodes['step-count'].textContent, `${index + 1} / ${story.steps.length}`);
    assert.equal(nodes['chapter-list'].children.filter(item => item.attributes['aria-current'] === 'step').length, 1);
    nodes.next.click();
  }
  assert.equal(nodes.next.disabled, true);
  page.key('ArrowRight');
  assert.equal(nodes['step-count'].textContent, `${story.steps.length} / ${story.steps.length}`);
  page.key('ArrowLeft');
  assert.equal(nodes['step-count'].textContent, `${story.steps.length - 1} / ${story.steps.length}`);
  page.key('r');
  assert.equal(nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  page.key('ArrowLeft');
  assert.equal(nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  page.key('ArrowRight', { target: new Element('input') });
  page.key('ArrowRight', { ctrlKey: true });
  assert.equal(nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  assert.equal(page.key('ArrowRight').prevented, true);
  assert.equal(nodes['step-count'].textContent, `2 / ${story.steps.length}`);
});

test('direct links and later hash changes restore the complete scene state', () => {
  for (const [index, step] of story.steps.entries()) {
    const page = browser(`#${step.id}`);
    assert.equal(page.nodes['step-count'].textContent, `${index + 1} / ${story.steps.length}`);
    assert.equal(page.nodes['scene-title'].textContent, step.title);
    const state = story.stateAt(index);
    assert.equal(state.rhelConfigurationApplied, step.stage >= 2, `${step.id}: direct-link RHEL state`);
    assert.equal(state.aapConfigurationApplied, index >= 4, `${step.id}: direct-link AAP settings state`);
    assert.equal(state.baseContentApplied, index >= 5, `${step.id}: direct-link content state`);
    assert.equal(page.nodes['target-objects'].hidden, !state.baseContentApplied, `${step.id}: direct-link content visibility`);
    assert.equal(page.nodes['target-configuration-panel'].hidden, !state.aapConfigurationApplied, `${step.id}: direct-link settings visibility`);
    assert.equal(objectNames(page.nodes['target-objects']).length, state.targetObjects.length);
    for (const prefix of ['source', 'target', 'successor']) {
      const expectedObjects = state[`${prefix}Objects`];
      assert.equal(automationItems(page.nodes[`${prefix}-objects`]).length, expectedObjects.length, `${step.id}: ${prefix} object count`);
      for (const item of automationItems(page.nodes[`${prefix}-objects`])) {
        const name = withClass(item, 'object-name')[0].textContent;
        const expected = expectedObjects.find(object => object.name === name);
        assert.ok(expected, `${step.id}: ${prefix} object ${name}`);
        assert.equal(item.dataset.origin, expected.origin, `${step.id}: ${name} retains its colour origin`);
        assert.equal(item.dataset.inGit, String(expected.inGit), `${step.id}: ${name} Git capture state`);
        const accessibleLabel = item.attributes['aria-label'];
        assert.ok(accessibleLabel?.includes(name), `${step.id}: ${name} has an accessible object name`);
        assert.match(accessibleLabel, new RegExp(expected.origin === 'base' ? 'base' : expected.origin === 'git' ? 'Git' : 'manual', 'i'));
        if (expected.origin === 'manual') {
          assert.match(accessibleLabel, expected.inGit ? /saved.*Git/i : /not.*saved.*Git/i, `${step.id}: accessible manual capture state`);
          if (expected.inGit) assert.doesNotMatch(accessibleLabel, /not.*saved/i);
        }
      }
      for (const suffix of ['objects', 'configuration', 'infrastructure']) {
        const root = page.nodes[`${prefix}-${suffix}`];
        for (const className of ['origin-label', 'git-badge', 'rhel-config-origin']) {
          assert.equal(withClass(root, className).length, 0, `${step.id}: ${prefix}-${suffix} has no repeated ${className} badges`);
        }
        for (const item of withClass(root, 'object-item')) {
          const name = withClass(item, 'object-name')[0];
          assert.ok(name, `${step.id}: each coloured bar has a name`);
          assert.equal(item.textContent, name.textContent, `${step.id}: coloured bars show their name without repeated badges`);
        }
      }
    }
  }
  const page = browser('#unrecognized');
  assert.equal(page.nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  page.hash('#capture');
  assert.equal(manualItems(page.nodes['target-objects']).filter(item => item.dataset.inGit === 'true').length, 3);
  page.hash('#manual');
  assert.equal(manualItems(page.nodes['target-objects']).length, 3);
  assert.ok(manualItems(page.nodes['target-objects']).every(item => item.dataset.inGit === 'false'));
  page.hash('#unrecognized');
  assert.equal(page.nodes['target-card'].hidden, true);
});

test('complete local files retain pinned sources and scroll each pane to its current section', () => {
  const page = browser('#project');
  for (const link of page.nodes['source-links'].children) {
    assert.ok(link.href.startsWith(story.sourceRoot));
    assert.equal(link.target, '_blank');
    assert.equal(link.rel, 'noopener noreferrer');
  }
  for (const file of ['src/app.js', 'src/scenario.js']) {
    assert.doesNotMatch(source(file), /\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(/);
    assert.doesNotMatch(source(file), /\b(?:setInterval|setTimeout)\s*\(/);
  }
  assert.equal(story.stateAt(story.steps.findIndex(step => step.id === 'capture')).targetObjects.filter(item => item.origin === 'manual' && item.inGit).length, 3);
  assert.equal(story.stateAt(story.steps.findIndex(step => step.id === 'manual')).targetObjects.filter(item => item.origin === 'manual' && item.inGit).length, 0);
  assert.throws(() => story.stateAt('capture'), TypeError);
  const publicFocus = {
    separation: ['project-resources', 'job-templates'], vm: ['vm'], infrastructure: ['certificate', 'firewall'], installation: ['installation'],
    'base-aap': ['aap-settings'], base: ['base-content'], project: ['project-resources', 'job-templates'],
    'git-change': ['aap-settings'], 'infra-change': ['certificate'],
    manual: ['capture-implementation'], capture: ['capture-implementation', 'capture-inputs'], 'next-aap': ['vm'],
    rebuild: ['vm', 'certificate', 'firewall', 'installation', 'aap-settings', 'base-content', 'project-resources', 'job-templates'],
  };
  const privateFocus = {
    separation: ['vm'], vm: ['vm'], infrastructure: ['certificate', 'firewall'], installation: ['installation'],
    'base-aap': ['logging', 'eda', 'aap-secrets'], 'git-change': ['logging'], 'infra-change': ['certificate'],
    manual: ['manual-note'], 'next-aap': ['vm'],
  };
  const privateSections = ['preamble', 'vm', 'certificate', 'firewall', 'installation', 'logging', 'eda', 'aap-secrets', 'inventories', 'inventory-sources', 'projects', 'credentials', 'job-templates', 'manual-note'];
  for (const [index, step] of story.steps.entries()) {
    for (const id of ['config-lines', 'code-lines']) {
      page.nodes[id].parentElement.scrollTop = 9999;
      page.nodes[id].parentElement.scrollLeft = 9999;
    }
    page.hash(`#${step.id}`);
    const state = story.stateAt(index);
    assert.equal(page.nodes['execution-file-name'].textContent, 'playbooks.yml · combined excerpts');
    for (const [id, entries] of [['config-lines', story.configurationLines(state)], ['code-lines', story.executionLines(state)]]) {
      const container = page.nodes[id];
      assert.equal(container.children.length, entries.length, `${step.id}: ${id} retains every line`);
      for (const [position, entry] of entries.entries()) {
        const rendered = container.children[position];
        assert.equal(rendered.children.slice(1).map(child => child.textContent).join(''), entry.text, `${step.id}: ${id} line text`);
        assert.equal(rendered.dataset.section, entry.section, `${step.id}: ${id} section metadata`);
        assert.equal(rendered.dataset.focus === 'true', Boolean(entry.focus), `${step.id}: ${id} focus metadata`);
        assert.equal(rendered.classList.contains('line-active'), Boolean(entry.active), `${step.id}: ${id} highlights only declared active lines`);
      }
      const focusedSections = [...new Set(entries.filter(entry => entry.focus).map(entry => entry.section))];
      const expectedFocus = id === 'code-lines' ? publicFocus[step.id] : privateFocus[step.id];
      if (expectedFocus) assert.deepEqual(focusedSections, expectedFocus, `${step.id}: ${id} focuses the matching workflow sections`);
      const firstFocus = entries.findIndex(entry => entry.focus);
      assert.ok(firstFocus >= 0, `${step.id}: ${id} has a scroll focus`);
      assert.equal(container.parentElement.scrollTop, Math.max(0, firstFocus * 24 - 6), `${step.id}: ${id} scrolls to its first focus using explicit simulated offsets`);
      assert.equal(container.parentElement.scrollLeft, 0, `${step.id}: ${id} starts at the left edge`);
      if (id === 'code-lines') {
        const activeSections = [...new Set(entries.filter(entry => entry.active).map(entry => entry.section))];
        assert.deepEqual(activeSections, step.routes.includes('flow-code') ? publicFocus[step.id] : [], `${step.id}: viewing a public section does not imply executing it`);
      } else {
        assert.deepEqual([...new Set(entries.map(entry => entry.section))], privateSections, `${step.id}: the private pane retains all input and object categories`);
        assert.ok(entries.every(entry => entry.illustrative), 'Private configuration remains an illustrative decrypted view');
        assert.ok(entries.every(entry => !entry.source && !entry.sources?.length), 'Private examples do not claim to be exact public source code');
        const text = entries.map(entry => entry.text).join('\n');
        assert.match(text, /!vault\s*\|/);
        assert.match(text, /\$ANSIBLE_VAULT;1\.1;AES256/);
        assert.match(text, /fake|illustrative/i);
        const certificateInputs = entries.filter(entry => entry.section === 'certificate').map(entry => entry.text).join('\n');
        assert.match(certificateInputs, /aap_test_subdomain:\s*["']?\{\{/);
        assert.match(certificateInputs, /vault_domain:\s*!vault\s*\|/);
        const firewallInputs = entries.filter(entry => entry.section === 'firewall').map(entry => entry.text).join('\n');
        assert.match(firewallInputs, /firewall_rule_encrypted:\s*!vault\s*\|/);
        assert.match(firewallInputs, /aap_management_native_plan:/);
        assert.match(firewallInputs, /rich_rule:\s*["']?\{\{\s*firewall_rule_encrypted\s*\}\}/);
        assert.doesNotMatch(text, /certificate_config_encrypted|firewall_job_inputs/, 'Private RHEL examples bind to the shown implementation');

        for (const section of ['vm', 'certificate', 'firewall', 'installation', 'aap-secrets']) {
          assert.ok(entries.some(entry => entry.section === section && entry.text.includes('!vault')), `${step.id}: ${section} includes an illustrative encrypted input`);
        }
      }
    }
  }

});

test('active routes remain visible and deployment actions name the current stage', () => {
  const html = source('index.html');
  for (const [name, contents] of [['HTML', html], ['presenter', source('src/app.js')], ['styles', source('src/styles.css')]]) {
    assert.doesNotMatch(contents, /active-cue|connection-detail|apply-detail|\bACTIVE\b/, `${name}: below-arrow labels are deleted rather than hidden`);
  }
  for (const routeId of ['flow-config', 'flow-code', ...futureRoutes]) {
    const markup = htmlRegion(html, routeId);
    assert.match(markup, /class="connection-caption"/, `${routeId}: its action caption remains`);
    assert.match(markup, /class="flow-packets"/, `${routeId}: travelling packet markup remains`);
    assert.ok(markup.indexOf('class="connection-caption"') < markup.indexOf('class="flow-packets"'), `${routeId}: action text precedes its arrow`);
  }
  const page = browser();
  const expected = [
    ['separation', null, []],
    ['vm', 'Create VM', ['flow-config', 'flow-code', 'flow-apply']],
    ['infrastructure', 'Prepare OS', ['flow-config', 'flow-code', 'flow-apply']],
    ['installation', 'Install AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['base-aap', 'Push AAP config', ['flow-config', 'flow-code', 'flow-apply']],
    ['base', 'Push AAP content', ['flow-config', 'flow-code', 'flow-apply']],
    ['infra-change', 'Push OS changes', ['flow-config', 'flow-code', 'flow-apply']],
    ['git-change', 'Push AAP config changes', ['flow-config', 'flow-code', 'flow-apply']],
    ['project', 'Push AAP content changes', ['flow-config', 'flow-code', 'flow-apply']],
    ['manual', null, []],
    ['capture', null, ['flow-scan', 'flow-return']],
    ['next-aap', null, []],
    ['rebuild', null, ['flow-config', 'flow-code', 'flow-rebuild']],
  ];
  for (const [id, caption, activeRoutes] of expected) {
    page.hash(`#${id}`);
    if (caption) {
      assert.equal(page.nodes['apply-caption'].textContent, caption, id);
    }
    for (const routeId of ['flow-config', 'flow-code', ...futureRoutes]) {
      const route = page.nodes[routeId];
      const active = activeRoutes.includes(routeId);
      assert.equal(route.classList.contains('active'), active, `${id}: ${routeId}`);
      const visible = active || routeId === 'flow-config' || routeId === 'flow-code';
      assert.equal(route.hidden, !visible, `${id}: ${routeId} visibility`);
      assert.equal(route.attributes['aria-hidden'], String(!visible), `${id}: ${routeId} accessibility`);
    }
  }
  // These dimensions test positioning arithmetic, not actual browser geometry.
  const { nodes, context } = page;
  const contentStages = ['base', 'project'];
  for (const id of contentStages) {
    nodes['source-card'].offsetTop = 300;
    nodes['apply-caption'].offsetHeight = 40;
    nodes['apply-track'].offsetHeight = 28;
    page.hash(`#${id}`);
    assert.equal(nodes['flow-apply'].dataset.destination, 'content', id);
    assert.equal(nodes['flow-apply'].style.top, '246px', `${id}: the content arrow starts at the original AAP top, allowing for its caption and half the track`);
    nodes['source-card'].offsetTop = 450;
    nodes['apply-caption'].offsetHeight = 60;
    nodes['apply-track'].offsetHeight = 32;
    assert.equal(typeof context.resize, 'function', 'Content alignment follows viewport changes');
    context.resize();
    assert.equal(nodes['flow-apply'].style.top, '374px', `${id}: resize recalculates alignment from the current card position and wrapped caption`);
  }
  for (const step of story.steps.filter(step => !contentStages.includes(step.id))) {
    page.hash(`#${step.id}`);
    assert.equal(nodes['flow-apply'].style.top, '', `${step.id}: content positioning does not leak into other stages`);
  }
  assert.match(source('src/styles.css'), /\.connector-route\s*\{[^}]*position:\s*relative;[^}]*top:\s*auto\s*!important;/, 'The existing narrow layout overrides desktop inline positioning');
});

test('the sidebar owns controls and status while three content columns own the diagram', () => {
  const html = source('index.html');
  const opening = html.match(/<aside\b[^>]*class="[^"]*\bsidebar\b[^"]*"[^>]*>/);
  assert.ok(opening, 'The walkthrough needs its sidebar');
  // The operator annotation is also an aside; stop at the matching outer close.
  let depth = 0;
  let sidebar = '';
  for (const tag of html.slice(opening.index).matchAll(/<\/?aside\b[^>]*>/gi)) {
    depth += tag[0].startsWith('</') ? -1 : 1;
    if (depth === 0) { sidebar = html.slice(opening.index, opening.index + tag.index + tag[0].length); break; }
  }
  assert.ok(sidebar, 'The sidebar has a matching closing tag');
  for (const id of ['chapter-list', 'previous', 'next', 'restart', 'step-count', 'progress-fill']) {
    assert.match(sidebar, new RegExp(`\\bid="${id}"`), `${id} belongs in the sidebar`);
  }
  for (const file of ['index.html', 'src/app.js', 'src/styles.css']) {
    assert.doesNotMatch(source(file), /\bfeedback\b/, `${file}: the bottom-left summary is deleted entirely`);
  }
  const footerOpening = sidebar.match(/<div\b[^>]*class="[^"]*\bsidebar-footer\b[^"]*"[^>]*>/);
  assert.ok(footerOpening, 'Navigation retains its dedicated footer');
  const footer = sidebar.slice(footerOpening.index);
  assert.match(footer, /class="[^"]*\bscene-controls\b/);
  assert.match(footer, /class="[^"]*\billustration-note\b/);
  assert.doesNotMatch(footer, /aria-live|\bid="(?:scene-title|chapter-list|job-status|target-state|actor|source-links)"/, 'Dynamic story content remains outside the navigation footer');
  const styles = source('src/styles.css');
  const footerRule = styles.match(/(?:^|\n)\.sidebar-footer\s*\{([^}]+)}/)[1];
  assert.match(footerRule, /flex:\s*none;/, 'The navigation footer retains its own height');
  assert.match(footerRule, /margin-top:\s*auto;/, 'The navigation footer stays anchored below scrollable story content');
  assert.match(styles, /(?:^|\n)\.sidebar-scroll\s*\{[^}]*flex:\s*1;[^}]*min-height:\s*0;[^}]*overflow-y:\s*auto;/, 'Dynamic sidebar content scrolls within its available space');
  assert.match(styles, /(?:^|\n)\.scene-controls\s*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*2\.1875rem\s+minmax\(0,\s*1fr\)\s+1\.6875rem;/, 'Navigation uses stable previous, Next and restart tracks');
  assert.match(styles, /(?:^|\n)\.button-step\s*\{[^}]*height:\s*2\.3125rem;/, 'Step buttons retain one height across chapters');
  const nextRule = styles.match(/(?:^|\n)\.button-next\s*\{([^}]+)}/)[1];
  assert.match(nextRule, /width:\s*100%;/);
  assert.match(nextRule, /min-width:\s*0;/);
  assert.match(nextRule, /white-space:\s*nowrap;/, 'Next and Complete labels cannot wrap and shift the controls');
  assert.doesNotMatch(sidebar, /\bid="legend"/, 'The origin legend has moved out of the sidebar');
  assert.equal((html.match(/\bid="legend"/g) || []).length, 1, 'One shared legend explains every coloured bar');
  const sourceColumn = htmlRegion(html, 'source-column');
  const sourceCard = htmlRegion(html, 'source-card');
  const legend = htmlRegion(html, 'legend');
  assert.ok(sourceColumn.includes(legend), 'The shared legend belongs in the original middle AAP column');
  assert.ok(sourceColumn.indexOf(legend) > sourceColumn.indexOf(sourceCard) + sourceCard.length, 'The shared legend follows the complete original AAP card');
  const legendText = legend.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  for (const [origin, text] of [
    ['base', 'Blue: Base CaC configuration at AAP deployment.'],
    ['git', 'Purple: New configuration and changes defined in CaC Git.'],
    ['manual', 'Yellow: Manual changes read from AAP configuration and pushed back into Git.'],
  ]) {
    assert.match(legend, new RegExp(`\\borigin-${origin}\\b`), `${origin}: legend retains its colour swatch`);
    assert.ok(legendText.includes(text), `${origin}: legend explains the configuration lifecycle`);
  }
  const main = html.match(/<main\b[^>]*id="story"[^>]*>/);
  assert.ok(main, 'The diagram keeps its main landmark');
  assert.match(main[0], /class="[^"]*\bcanvas-shell\b/);
  assert.doesNotMatch(html, /class="[^"]*\b(?:introduction|hero|scene-heading)\b[^"]*"/);
  const regions = [
    html.search(/class="[^"]*\brepository-column\b/),
    html.search(/class="[^"]*\brepository-connections\b/),
    html.indexOf('id="source-card"'),
    html.search(/class="[^"]*\binstance-connections\b/),
    html.search(/class="[^"]*\breceiving-slot\b/),
  ];
  assert.ok(regions.every(position => position >= 0), 'All three content columns and their connectors exist');
  assert.deepEqual([...regions].sort((left, right) => left - right), regions, 'Repositories, original AAP and receiving AAP remain in reading order');
  for (const id of ['config-card', 'code-card']) {
    const position = html.indexOf(`id="${id}"`);
    assert.ok(position > regions[0] && position < regions[1], `${id} belongs in the repository column`);
  }
  assert.ok(html.indexOf('id="target-card"') > regions[4], 'The new AAP belongs in the receiving column');
});


test('active arrows match the highlighted configuration origin and reset on navigation', () => {
  const page = browser();
  for (const [id, origin, names] of [
    ['base-aap', 'base', ['AAP Logging Config v1', 'AAP EDA Config v1']],
    ['base', 'base', ['VMWare Inventory', 'AAP Config-as-Code Git']],
    ['project', 'git', ['Satellite Inventory', 'Application automation playbooks', 'Regional servers', 'Regional automation']],
    ['git-change', 'git', ['AAP Logging Config v2']],
    ['infra-change', 'git', ['Certificate config v2']],
    ['capture', 'manual', ['Emergency servers', 'Quick-fix automation']],
    ['vm', 'base', ['!vault']],
    ['infrastructure', 'base', ['firewall_rule_encrypted', 'vault_domain', 'aap_test_subdomain']],
    ['installation', 'base', ['!vault']],
  ]) {
    page.hash(`#${id}`);
    const activeRoutes = ['flow-config', 'flow-code', ...futureRoutes].map(route => page.nodes[route]).filter(route => route.classList.contains('active'));
    assert.ok(activeRoutes.length > 0, id);
    for (const route of activeRoutes) assert.equal(route.dataset.origin, origin, `${id}: route origin`);
    const highlighted = withClass(page.nodes['config-lines'], 'line-active');
    assert.ok(highlighted.length > 0, `${id}: highlighted configuration`);
    for (const line of highlighted) assert.equal(line.dataset.origin, origin, `${id}: configuration origin`);
    for (const name of names) assert.ok(highlighted.some(line => line.textContent.includes(name)), `${id}: ${name}`);
    if (['base-aap', 'base'].includes(id)) {
      const categories = {
        infrastructure: ['Certificate config v1', 'Firewall Config v1'],
        'base-aap': ['AAP Logging Config v1', 'AAP EDA Config v1'],
        base: ['VMWare Inventory', 'AAP Config-as-Code Git', 'Server access key', 'AAP Config-as-Code jobs'],
      };
      for (const [category, categoryNames] of Object.entries(categories)) {
        if (category !== id) {
          for (const name of categoryNames) assert.ok(!highlighted.some(line => line.textContent.includes(name)), `${id}: ${name} is outside the current apply category`);
        }
      }
    }
    const execution = withClass(page.nodes['code-lines'], 'line-active');
    if (id === 'capture') assert.equal(execution.length, 0, 'Capture writes CaC without claiming to read code');
    else {
      assert.ok(execution.length > 0, `${id}: highlighted playbook`);
      for (const line of execution) assert.equal(line.dataset.origin, origin, `${id}: playbook origin`);
    }
  }
  page.hash('#manual');
  assert.equal(withClass(page.nodes['config-lines'], 'line-active').length, 0);
  assert.equal(withClass(page.nodes['code-lines'], 'line-active').length, 0);
});


test('base AAP configuration is deployed and Git updates replace logging without changing EDA', () => {
  const page = browser();
  const { nodes } = page;
  const names = id => objectNames(nodes[id]);
  assert.deepEqual(names('source-configuration'), ['AAP Logging Config v1', 'AAP EDA Config v1']);
  assert.equal(nodes['target-configuration-panel'].hidden, true);
  for (const id of ['vm', 'infrastructure', 'installation']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-configuration-panel'].hidden, true);
    assert.deepEqual(names('target-configuration'), []);
  }
  for (const id of ['base-aap', 'base', 'infra-change']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-configuration-panel'].hidden, false);
    assert.deepEqual(names('target-configuration'), ['AAP Logging Config v1', 'AAP EDA Config v1']);
    for (const item of withClass(nodes['target-configuration'], 'configuration-item')) assert.equal(item.dataset.origin, 'base');
  }
  for (const id of ['git-change', 'project', 'manual', 'capture', 'next-aap', 'rebuild']) {
    page.hash(`#${id}`);
    assert.deepEqual(names('target-configuration'), ['AAP Logging Config v2', 'AAP EDA Config v1']);
    const configs = withClass(nodes['target-configuration'], 'configuration-item');
    assert.equal(configs.filter(item => item.dataset.configId === 'logging').length, 1, 'Logging is updated, not duplicated');
    assert.equal(configs.find(item => item.dataset.configId === 'logging').dataset.origin, 'git');
    assert.equal(configs.find(item => item.dataset.configId === 'eda').dataset.origin, 'base');
    assert.deepEqual(names('source-configuration'), ['AAP Logging Config v1', 'AAP EDA Config v1']);
    assert.match(nodes['config-lines'].textContent, /AAP Logging Config v2/);
    assert.doesNotMatch(nodes['config-lines'].textContent, /AAP Logging Config v1/);
  }
  page.hash('#git-change');
  assert.equal(nodes['job-label'].textContent, 'Apply configuration');
  const logging = withClass(nodes['config-lines'], 'line-active').filter(line => line.textContent.includes('LOG_AGGREGATOR_ACTION_QUEUE_SIZE'));
  assert.equal(logging.length, 1);
  assert.equal(logging[0].dataset.origin, 'git');
  assert.match(logging[0].textContent, /20000/);
  assert.ok(nodes['source-links'].children.some(link => link.href.endsWith('/04-aap-config.yml')));
  page.hash('#base');
  assert.deepEqual(names('target-configuration'), ['AAP Logging Config v1', 'AAP EDA Config v1']);
  assert.match(nodes['config-lines'].textContent, /LOG_AGGREGATOR_ACTION_QUEUE_SIZE: 10000/);
  nodes.restart.click();
  assert.equal(nodes['target-configuration-panel'].hidden, true);
  assert.deepEqual(names('target-configuration'), []);
});


test('another AAP receives the complete Git snapshot only after capture and reverses cleanly', () => {
  const page = browser();
  const { nodes } = page;
  const originalObjects = objectNames(nodes['source-objects']);
  const originalConfiguration = objectNames(nodes['source-configuration']);
  const originalInfrastructure = objectNames(nodes['source-infrastructure']);
  for (const step of story.steps.slice(0, -1)) {
    page.hash(`#${step.id}`);
    assert.equal(nodes['successor-card'].hidden, true, step.id);
    assert.equal(nodes['successor-card'].attributes['aria-hidden'], 'true', step.id);
    assert.equal(nodes['successor-placeholder'].hidden, step.id !== 'next-aap', step.id);
    assert.deepEqual(objectNames(nodes['successor-objects']), [], step.id);
    assert.deepEqual(objectNames(nodes['successor-configuration']), [], step.id);
    assert.deepEqual(objectNames(nodes['successor-infrastructure']), [], step.id);
    assert.equal(story.stateAt(story.steps.indexOf(step)).successorVisible, false, step.id);
  }
  const captured = story.stateAt(story.steps.findIndex(step => step.id === 'capture'));
  page.hash('#rebuild');
  assert.equal(nodes['successor-card'].hidden, false);
  assert.equal(nodes['successor-card'].attributes['aria-hidden'], 'false');
  assert.equal(nodes['successor-placeholder'].hidden, true);
  assert.deepEqual(objectNames(nodes['successor-objects']).sort(), captured.configObjects.map(object => object.name).sort());
  assert.deepEqual(objectNames(nodes['successor-configuration']), ['AAP Logging Config v2', 'AAP EDA Config v1']);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), ['Certificate config v2', 'Firewall Config v1']);
  const successorItems = automationItems(nodes['successor-objects']);
  assert.equal(successorItems.length, 13);
  const html = source('index.html');
  for (const prefix of ['target', 'successor']) {
    const columns = withClass(nodes[`${prefix}-objects`], 'aap-object-column');
    assert.equal(columns.length, 2, `${prefix}: exactly two independent receiving object columns`);
    assert.deepEqual(withClass(columns[0], 'object-type').map(item => item.textContent.split(' · ')[0]), ['Inventories', 'Credentials']);
    assert.deepEqual(withClass(columns[1], 'object-type').map(item => item.textContent.split(' · ')[0]), ['Projects', 'Job Templates']);
    assert.ok(columns.every(column => !descendants(column).includes(nodes[`${prefix}-configuration-panel`])), `${prefix}: AAP settings are separate from both automation columns`);
    const panel = html.match(new RegExp(`<section\\b[^>]*\\bid="${prefix}-configuration-panel"[^>]*>`));
    assert.ok(panel);
    assert.match(panel[0], /class="[^"]*\baap-settings-panel\b/, `${prefix}: the separate settings category uses its inset divider style`);
    assert.match(html, new RegExp(`<div\\b[^>]*\\bid="${prefix}-objects"[^>]*>\\s*</div>`), `${prefix}: the settings panel is not nested inside the static catalogue`);
    const ordered = [`id="${prefix}-objects"`, `id="${prefix}-configuration-panel"`, `id="${prefix}-rhel"`].map(id => html.indexOf(id));
    assert.ok(ordered.every(position => position >= 0));
    assert.deepEqual([...ordered].sort((left, right) => left - right), ordered, `${prefix}: automation is followed by AAP settings, then RHEL`);
  }
  const styles = source('src/styles.css');
  assert.match(styles, /\.receiving-column \.aap-content\s*\{[^}]*display:\s*flex;[^}]*flex-direction:\s*column;/, 'Receiving content declares independent vertical layout');
  assert.match(styles, /\.receiving-column \.aap-content\s*\{[^}]*align-items:\s*stretch;/, 'Receiving catalogues and settings must stretch across the body instead of inheriting shrink-to-content alignment');
  const receivingLayout = styles.match(/(?:^|\n)\.receiving-column\s*\{([^}]+)}/)[1];
  assert.match(receivingLayout, /--aap-inset:\s*2cqw;/, 'Each receiving stack starts a small distance inside its half');
  assert.match(receivingLayout, /--aap-bar-width:\s*43cqw;/, 'Receiving bars retain one proportional width across categories');
  assert.match(receivingLayout, /--aap-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/, 'Automation and AAP settings use equal half-column tracks');
  assert.doesNotMatch(receivingLayout, /--aap-gutter\s*:/, 'The superseded equal-gutter layout is removed');
  assert.match(styles, /\.receiving-column \.aap-card\s*\{[^}]*container-type:\s*inline-size;/, 'Each receiving card supplies the same proportional width context to all its bars');
  assert.match(styles, /\.receiving-column \.aap-content\s*\{[^}]*padding:\s*6px\s+0;/, 'Body padding does not shift the two half-column tracks');
  assert.match(styles, /\.object-list\.receiving-catalog\s*\{[^}]*grid-template-columns:\s*var\(--aap-columns\);[^}]*gap:\s*0;/, 'The catalogue starts each stack in its respective half');
  for (const [label, rule] of [
    ['Object columns', /(?:^|\n)\.aap-object-column\s*\{([^}]+)}/],
    ['AAP settings', /\.aap-settings-panel \.configuration-item\s*\{([^}]+)}/],
    ['RHEL settings', /\.receiving-column \.rhel-foundation > \.configuration-panel\s*\{([^}]+)}/],
  ]) {
    const match = styles.match(rule);
    assert.ok(match, `${label}: scoped bar layout exists`);
    assert.match(match[1], /width:\s*var\(--aap-bar-width\);/, `${label}: bars share the same relative width`);
    assert.match(match[1], /margin-inline-start:\s*var\(--aap-inset\);/, `${label}: bars left-align with a small inset`);
  }
  assert.match(styles, /\.receiving-catalog \.object-item,\.aap-settings-panel \.object-item\s*\{[^}]*margin:\s*\.125rem\s+0;/, 'Receiving automation bars use compact vertical spacing');
  assert.match(styles, /\.receiving-column \.aap-settings-panel\s*\{[^}]*margin:\s*auto\s+0\s+0;/, 'Settings keep bottom anchoring');
  assert.match(styles, /\.aap-settings-panel \.configuration-list\s*\{[^}]*grid-template-columns:\s*var\(--aap-columns\);[^}]*gap:\s*\.1875rem\s+0;/, 'AAP settings preserve the same halves with compact vertical gaps');
  assert.match(styles, /\.aap-settings-panel::before\s*\{[^}]*left:\s*var\(--aap-inset\);[^}]*right:\s*var\(--aap-inset\);/, 'The divider follows the small outer inset');
  const rhelReceiving = styles.match(/\.receiving-column \.rhel-foundation\s*\{([^}]+)}/)[1];
  assert.match(rhelReceiving, /grid-template-columns:\s*minmax\(0,\s*calc\(50cqw\s*-\s*\.5rem\)\)\s+minmax\(0,\s*1fr\);/, 'RHEL compensates its inset border so configuration starts in the right half');
  assert.match(rhelReceiving, /column-gap:\s*0;/);
  assert.match(rhelReceiving, /border-width:\s*\.125rem;/);
  assert.match(rhelReceiving, /border-left-width:\s*\.25rem;/);
  assert.match(rhelReceiving, /margin:\s*0\s+\.25rem\s+\.5rem;/);
  assert.match(rhelReceiving, /padding:\s*\.375rem\s+0;/);
  assert.match(styles, /(?:^|\n)\.object-name\s*\{[^}]*font-size:\s*\.9375rem;/, 'Object names use the larger bar-only text size');
  assert.match(styles, /\.rhel-foundation \.object-name\s*\{[^}]*font-size:\s*\.875rem;/, 'RHEL names use the larger bar-only text size');
  assert.match(styles, /\.aap-settings-panel::before\s*\{[^}]*border-top:\s*1px solid/, 'The category has one thin separator');
  assert.equal(successorItems.filter(item => item.dataset.origin === 'base').length, 4);
  assert.equal(successorItems.filter(item => item.dataset.origin === 'git').length, 6);
  assert.equal(successorItems.filter(item => item.dataset.origin === 'manual').length, 3);
  assert.ok(successorItems.every(item => item.dataset.inGit === 'true'), 'Replay retains the complete captured Git snapshot');
  for (const item of manualItems(nodes['successor-objects'])) {
    assert.equal(item.dataset.origin, 'manual', 'Replayed manual objects retain their yellow origin');
    assert.equal(item.dataset.inGit, 'true');
  }
  assert.deepEqual(objectNames(nodes['target-objects']).sort(), captured.targetObjects.map(object => object.name).sort());
  assert.deepEqual(objectNames(nodes['target-configuration']), ['AAP Logging Config v2', 'AAP EDA Config v1']);
  assert.deepEqual(objectNames(nodes['source-objects']), originalObjects);
  assert.deepEqual(objectNames(nodes['source-configuration']), originalConfiguration);
  assert.deepEqual(objectNames(nodes['source-infrastructure']), originalInfrastructure);
  assert.equal(nodes['flow-rebuild'].hidden, false);
  assert.equal(nodes['flow-rebuild'].classList.contains('active'), true);
  assert.equal(nodes['flow-config'].classList.contains('active'), true);
  assert.equal(nodes['flow-code'].classList.contains('active'), true);
  for (const id of ['flow-apply', 'flow-scan', 'flow-return']) assert.equal(nodes[id].hidden, true, id);
  const replay = story.stateAt(story.steps.length - 1);
  assert.equal(replay.successorVisible, true);
  assert.equal(new Set(replay.successorObjects.map(object => object.id)).size, 13);
  assert.ok(replay.successorObjects.every(object => object.inGit));
  const expectedObjectName = replay.targetObjects[0].name;
  replay.successorObjects[0].name = 'Changed replay fixture';
  assert.equal(replay.targetObjects[0].name, expectedObjectName, 'Replay does not alias the first target');
  assert.notEqual(replay.configObjects[0].name, 'Changed replay fixture', 'Replay does not mutate Git definitions');
  replay.successorConfiguration[0].name = 'Changed configuration fixture';
  assert.equal(replay.targetConfiguration[0].name, 'AAP Logging Config v2');
  assert.equal(story.stateAt(story.steps.length - 1).successorConfiguration[0].name, 'AAP Logging Config v2');
  replay.successorInfrastructure[0].name = 'Changed infrastructure fixture';
  assert.equal(replay.targetInfrastructure[0].name, 'Certificate config v2');
  assert.equal(story.stateAt(story.steps.length - 1).successorInfrastructure[0].name, 'Certificate config v2');
  nodes.previous.click();
  assert.equal(nodes['successor-card'].hidden, true);
  assert.deepEqual(objectNames(nodes['successor-objects']), []);
  assert.deepEqual(objectNames(nodes['successor-configuration']), []);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), []);
  assert.equal(manualItems(nodes['target-objects']).filter(item => item.dataset.inGit === 'true').length, 3, 'Captured first target is retained');
  page.hash('#rebuild');
  nodes.restart.click();
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(nodes['successor-placeholder'].hidden, true);
  assert.deepEqual(objectNames(nodes['successor-objects']), []);
  assert.deepEqual(objectNames(nodes['successor-configuration']), []);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), []);
});

test('the sidebar marks completed chapters and follows only a changed current chapter', () => {
  const page = browser();
  const buttons = page.nodes['chapter-list'].children;
  assert.equal(buttons.length, 7);
  const last = buttons.at(-1);
  assert.equal(last.scrollRequests.length, 0);
  for (const [current, chapter] of story.chapters.entries()) {
    page.chapter(chapter.id);
    assert.equal(page.nodes['step-count'].textContent, `${chapter.index + 1} / ${story.steps.length}`);
    for (const [position, button] of buttons.entries()) {
      assert.equal(button.classList.contains('complete'), position < current, `${chapter.id}: completed chapter`);
      assert.equal(button.attributes['aria-current'] === 'step', position === current, `${chapter.id}: current chapter`);
    }
  }
  assert.equal(last.scrollRequests.length, 1, 'The newly current chapter is brought into view');
  assert.equal(last.scrollRequests[0].block, 'nearest');
  page.hash('#rebuild');
  assert.equal(last.scrollRequests.length, 1, 'Rendering the same chapter preserves its scroll position');
  page.chapter('deployment');
  const deployment = buttons.find(button => button.dataset.chapter === 'deployment');
  const requests = deployment.scrollRequests.length;
  page.nodes.next.click();
  assert.equal(deployment.scrollRequests.length, requests, 'Advancing inside a chapter does not scroll it again');
  assert.equal(deployment.attributes['aria-current'], 'step');
  page.chapter('git-change');
  const gitChapter = buttons.find(button => button.dataset.chapter === 'git-change');
  const gitRequests = gitChapter.scrollRequests.length;
  page.nodes.next.click();
  assert.equal(page.nodes['job-label'].textContent, 'Apply configuration');
  assert.equal(gitChapter.scrollRequests.length, gitRequests, 'The logging substep retains the current Git chapter');
  assert.equal(gitChapter.attributes['aria-current'], 'step');
});


test('infrastructure configuration updates certificates while retaining firewall and source revisions', () => {
  assert.doesNotMatch(source('src/scenario.js'), /Monitoring Agent Config/, 'Monitoring profiles are removed from the story');
  const page = browser();
  const { nodes } = page;
  const names = id => objectNames(nodes[id]);
  const original = ['Certificate config v1', 'Firewall Config v1'];
  const updated = ['Certificate config v2', 'Firewall Config v1'];
  assert.deepEqual(names('source-infrastructure'), original);
  for (const id of ['separation', 'vm', 'infrastructure', 'installation']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-infrastructure-panel'].hidden, ['separation', 'vm'].includes(id), id);
    assert.deepEqual(names('target-infrastructure'), ['separation', 'vm'].includes(id) ? [] : original, id);
  }
  for (const id of ['base-aap', 'base']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-infrastructure-panel'].hidden, false, id);
    assert.deepEqual(names('target-infrastructure'), original, id);
    for (const item of withClass(nodes['target-infrastructure'], 'configuration-item')) assert.equal(item.dataset.origin, 'base');
  }
  for (const id of ['infra-change', 'git-change', 'project', 'manual', 'capture', 'next-aap', 'rebuild']) {
    page.hash(`#${id}`);
    assert.deepEqual(names('target-infrastructure'), updated, id);
    assert.deepEqual(names('source-infrastructure'), original, id);
    const configurations = withClass(nodes['target-infrastructure'], 'configuration-item');
    assert.equal(configurations.filter(item => item.dataset.configId === 'certificate').length, 1, 'Certificates are replaced, not duplicated');
    assert.equal(configurations.find(item => item.dataset.configId === 'certificate').dataset.origin, 'git');
    assert.equal(configurations.find(item => item.dataset.configId === 'firewall').dataset.origin, 'base');
    assert.match(nodes['config-lines'].textContent, /Certificate config v2/);
    assert.doesNotMatch(nodes['config-lines'].textContent, /Certificate config v1|Monitoring Agent Config/);
  }
  page.hash('#infra-change');
  assert.equal(nodes['job-label'].textContent, 'Apply infrastructure configuration');
  assert.equal(nodes['apply-caption'].textContent, 'Push OS changes');
  const highlighted = withClass(nodes['config-lines'], 'line-active');
  assert.ok(highlighted.some(line => /Certificate config v2/.test(line.textContent)), 'The updated certificate definition is highlighted');
  for (const line of highlighted) assert.equal(line.dataset.origin, 'git');
  nodes.previous.click();
  assert.deepEqual(names('target-infrastructure'), original, 'Backing up restores the previous infrastructure revision');
  assert.deepEqual(names('target-configuration'), ['AAP Logging Config v1', 'AAP EDA Config v1'], 'The logging update follows the RHEL update');
  page.hash('#rebuild');
  assert.deepEqual(names('successor-infrastructure'), updated);
  nodes.restart.click();
  assert.equal(nodes['target-infrastructure-panel'].hidden, true);
  assert.deepEqual(names('target-infrastructure'), []);
  assert.deepEqual(names('successor-infrastructure'), []);
});


test('the RHEL foundation follows deployment without implying a guest OS upgrade', () => {
  assert.doesNotMatch(source('index.html'), /id="(?:target|successor)-rhel-status"/, 'Both unwanted status spans are removed from the page');
  assert.doesNotMatch(source('src/app.js'), /-rhel-status|-rhel-detail|Host networking prepared/, 'The presenter does not write removed status fields');
  const page = browser();
  const { nodes } = page;
  assert.equal(nodes['target-rhel'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
  const milestones = id => withClass(nodes[id], 'rhel-milestone').map(item => [item.textContent, item.dataset.state]);
  for (const [id, stage, states] of [
    ['vm', '1', ['complete', 'current', 'pending']],
    ['infrastructure', '2', ['complete', 'current', 'pending']],
    ['installation', '3', ['complete', 'complete', 'complete']],
    ['base-aap', '4', ['complete', 'complete', 'complete']],
    ['base', '4', ['complete', 'complete', 'complete']],
  ]) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-rhel'].hidden, false, id);
    assert.equal(nodes['target-rhel'].dataset.stage, stage, id);
    assert.deepEqual(milestones('target-rhel-progress'), ['VM created', 'OS prepared', 'AAP installed'].map((name, index) => [name, states[index]]), id);
    assert.equal(nodes['successor-rhel'].hidden, true, id);
  }
  page.hash('#vm');
  assert.equal(nodes['target-rhel'].dataset.stage, '1', 'Backing up restores the VM-only foundation');
  assert.equal(milestones('target-rhel-progress')[1][1], 'current');
  nodes.restart.click();
  assert.equal(nodes['target-rhel'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
});

test('the RHEL foundation persists under AAP changes and replays into the third AAP', () => {
  const page = browser('#base');
  const { nodes } = page;
  const states = id => withClass(nodes[id], 'rhel-milestone').map(item => item.dataset.state);
  for (const id of ['project', 'git-change', 'infra-change', 'manual', 'capture']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-rhel'].hidden, false, id);
    assert.deepEqual(states('target-rhel-progress'), ['complete', 'complete', 'complete'], id);
    assert.equal(nodes['successor-rhel'].hidden, true, id);
  }
  page.hash('#rebuild');
  assert.equal(nodes['successor-rhel'].hidden, false);
  assert.equal(nodes['successor-rhel'].dataset.stage, '4');
  assert.deepEqual(states('successor-rhel-progress'), ['complete', 'complete', 'complete']);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), ['Certificate config v2', 'Firewall Config v1'], 'Both infrastructure profiles remain inside the receiving RHEL foundation');
  nodes.previous.click();
  assert.equal(nodes['successor-rhel'].hidden, true);
  assert.equal(nodes['target-rhel'].hidden, false);
  assert.deepEqual(states('target-rhel-progress'), ['complete', 'complete', 'complete']);
  page.hash('#rebuild');
  nodes.restart.click();
  assert.equal(nodes['target-rhel'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
});


test('RHEL profiles keep one renderer, order and placement through setup, base apply and replay', () => {
  const html = source('index.html');
  const app = source('src/app.js');
  const styles = source('src/styles.css');
  for (const [name, text] of [['HTML', html], ['presenter', app], ['styles', styles]]) {
    assert.doesNotMatch(text, /rhel-config(?:s|-name|-origin)\b/, `${name}: the duplicate early RHEL renderer is removed`);
  }
  assert.match(styles, /\.rhel-foundation > \.configuration-panel\s*\{[^}]*align-self:\s*start;/, 'The shared RHEL stack keeps a stable top anchor');
  const page = browser();
  const { nodes } = page;
  const original = ['Certificate config v1', 'Firewall Config v1'];
  const updated = ['Certificate config v2', 'Firewall Config v1'];
  const check = (id, index) => {
    const step = story.steps[index];
    const changed = index >= story.steps.findIndex(item => item.id === 'infra-change');
    const landing = ['infrastructure', 'infra-change'].includes(id);
    for (const prefix of ['source', 'target', 'successor']) {
      const visible = prefix === 'source' || (prefix === 'target' ? step.stage >= 2 : id === 'rebuild');
      const items = withClass(nodes[`${prefix}-infrastructure`], 'configuration-item');
      const expected = prefix === 'source' || !changed ? original : updated;
      assert.deepEqual(items.map(item => item.dataset.configId), visible ? ['certificate', 'firewall'] : [], `${id}: ${prefix} keeps certificate above firewall`);
      assert.deepEqual(objectNames(nodes[`${prefix}-infrastructure`]), visible ? expected : [], `${id}: ${prefix} canonical profile names`);
      if (visible) {
        assert.equal(items[0].dataset.origin, prefix !== 'source' && changed ? 'git' : 'base', `${id}: ${prefix} certificate colour`);
        assert.equal(items[1].dataset.origin, 'base', `${id}: ${prefix} firewall remains blue`);
        assert.ok(items.every(item => item.classList.contains('object-item')), `${id}: ${prefix} uses the same profile bar style`);
      }
    }
    assert.equal(nodes['target-infrastructure-panel'].hidden, step.stage < 2, `${id}: shared RHEL panel visibility`);
    assert.equal(nodes['target-rhel'].classList.contains('landing'), landing, `${id}: RHEL apply cue`);
    assert.equal(nodes['flow-apply'].dataset.destination, landing ? 'rhel' : ['base', 'project'].includes(id) ? 'content' : 'aap', `${id}: apply destination`);
    assert.equal(nodes['successor-rhel'].classList.contains('landing'), false, `${id}: replay does not retain a first-target apply cue`);
  };
  for (const [index, step] of story.steps.entries()) {
    page.hash(`#${step.id}`);
    check(step.id, index);
  }
  for (let index = story.steps.length - 2; index >= 0; index--) {
    nodes.previous.click();
    check(story.steps[index].id, index);
  }
  page.hash('#infra-change');
  assert.equal(nodes['flow-apply'].dataset.origin, 'git', 'The infrastructure update uses the purple Git route');
  nodes.restart.click();
  check('separation', 0);
});


test('the third destination placeholder appears only immediately before replay', () => {
  const html = source('index.html');
  const placeholderOpening = html.match(/<[^>]*\bid="successor-placeholder"[^>]*>/);
  assert.ok(placeholderOpening);
  assert.match(placeholderOpening[0], /\bhidden\b/);
  assert.match(placeholderOpening[0], /aria-hidden="true"/);
  assert.deepEqual(story.steps.slice(-2).map(step => step.id), ['next-aap', 'rebuild']);
  const page = browser();
  const { nodes } = page;
  for (const step of story.steps.slice(0, -2)) {
    page.hash(`#${step.id}`);
    assert.equal(story.stateAt(story.steps.indexOf(step)).successorPlaceholderVisible, false, step.id);
    assert.equal(nodes['successor-placeholder'].hidden, true, step.id);
    assert.equal(nodes['successor-placeholder'].attributes['aria-hidden'], 'true', step.id);
    assert.equal(nodes['successor-card'].hidden, true, step.id);
    assert.equal(nodes['successor-rhel'].hidden, true, step.id);
  }
  page.chapter('rebuild');
  assert.equal(nodes['step-count'].textContent, `${story.steps.length - 1} / ${story.steps.length}`);
  assert.equal(story.stateAt(story.steps.length - 2).successorPlaceholderVisible, true);
  assert.equal(nodes['successor-placeholder'].hidden, false);
  assert.equal(nodes['successor-placeholder'].attributes['aria-hidden'], 'false');
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
  assert.equal(nodes['flow-rebuild'].hidden, true);
  nodes.next.click();
  assert.equal(nodes['successor-placeholder'].hidden, true);
  assert.equal(nodes['successor-placeholder'].attributes['aria-hidden'], 'true');
  assert.equal(nodes['successor-card'].hidden, false);
  assert.equal(nodes['successor-rhel'].hidden, false);
  assert.equal(nodes['flow-rebuild'].hidden, false);
  nodes.previous.click();
  assert.equal(nodes['successor-placeholder'].hidden, false, 'Backing up from deployment restores only the interim destination');
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
  nodes.previous.click();
  assert.equal(nodes['successor-placeholder'].hidden, true, 'The main story leaves the lower slot blank');
  page.chapter('rebuild');
  nodes.restart.click();
  assert.equal(nodes['successor-placeholder'].hidden, true);
  assert.equal(nodes['successor-placeholder'].attributes['aria-hidden'], 'true');
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(nodes['successor-rhel'].hidden, true);
});


test('the incident-response sysadmin appears only for direct manual AAP changes', () => {
  const html = source('index.html');
  const opening = html.match(/<[^>]*\bid="manual-operator"[^>]*>/);
  assert.ok(opening);
  const figure = html.slice(opening.index, html.indexOf('</figure>', opening.index) + '</figure>'.length);
  const slot = htmlRegion(html, 'manual-operator-slot');
  const sourceColumn = htmlRegion(html, 'source-column');
  const slotOpening = slot.slice(0, slot.indexOf('>') + 1);
  assert.match(slotOpening, /class="[^"]*\bmanual-operator-slot\b/);
  assert.doesNotMatch(slotOpening, /\shidden(?:\s|=|>)|aria-hidden="true"/, 'The reserved operator space remains visible before the sysadmin appears');
  assert.ok(slot.includes(figure), 'The conditional sysadmin figure sits inside the persistent slot');
  assert.ok(sourceColumn.includes(slot), 'The operator slot belongs to the original AAP column');
  assert.ok(sourceColumn.indexOf(slot) + slot.length < sourceColumn.indexOf('id="source-card"'), 'The persistent slot reserves space above the original AAP');
  const styles = source('src/styles.css');
  const slotRule = styles.match(/(?:^|\n)\.manual-operator-slot\s*\{([^}]+)}/);
  assert.ok(slotRule, 'The reserved operator slot declares its own layout');
  assert.match(slotRule[1], /height:\s*11\.25rem;/);
  assert.match(slotRule[1], /flex:\s*none;/);
  assert.match(slotRule[1], /min-width:\s*0;/);
  assert.match(styles, /(?:^|\n)\.manual-operator\s*\{[^}]*height:\s*100%;/, 'The conditional figure fills the already reserved slot');
  for (const [file, text] of [['presenter', source('src/app.js')], ['styles', styles]]) {
    assert.doesNotMatch(text, /manual-active/, `${file}: the manual scene does not switch the source layout`);
  }
  const image = figure.match(/<img\b([^>]*\bclass="[^"]*\bsysadmin-illustration\b[^"]*"[^>]*)>/);
  assert.ok(image, 'The sysadmin uses its generated local image');
  const imageAttributes = attributes(new Element('img'), image[1]).attributes;
  assert.equal(imageAttributes.src, 'sysadmin.png');
  assert.equal(imageAttributes.alt, '', 'The visible figure caption provides the description');
  assert.equal(imageAttributes['aria-hidden'], 'true');
  assert.doesNotMatch(figure, /<svg\b[^>]*\bclass="[^"]*\bsysadmin-illustration\b/, 'The old sysadmin SVG is removed');
  const png = readFileSync(path.join(demo, imageAttributes.src));
  assert.ok(png.length <= 8 * 1024 * 1024, 'The image stays within the live checker limit');
  assert.ok(png.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex')), 'The local image is PNG');

  assert.match(opening[0], /\bhidden\b/);
  assert.match(opening[0], /aria-hidden="true"/);
  const page = browser();
  const { nodes } = page;
  const sourceCard = nodes['source-card'];
  const reservedSlot = nodes['manual-operator-slot'];
  const checkReservedLayout = () => {
    assert.equal(nodes['source-card'], sourceCard, 'Navigation preserves the original AAP card');
    assert.equal(nodes['manual-operator-slot'], reservedSlot, 'Navigation preserves the reserved operator wrapper');
    assert.equal(reservedSlot.hidden, false, 'The empty operator slot remains in the layout');
    assert.notEqual(reservedSlot.attributes['aria-hidden'], 'true');
    assert.equal(sourceCard.hidden, false);
    assert.equal(nodes['source-column'].classList.contains('manual-active'), false);
  };
  checkReservedLayout();
  for (const step of story.steps.filter(step => step.id !== 'manual')) {
    page.hash(`#${step.id}`);
    checkReservedLayout();
    assert.equal(nodes['manual-operator'].hidden, true, step.id);
    assert.equal(nodes['manual-operator'].attributes['aria-hidden'], 'true', step.id);
  }
  page.chapter('manual');
  checkReservedLayout();
  assert.equal(nodes['manual-operator'].hidden, false);
  assert.equal(nodes['manual-operator'].attributes['aria-hidden'], 'false');
  assert.equal(nodes['manual-operator-title'].textContent, 'Sysadmin · incident response');
  assert.equal(nodes['manual-operator-description'].textContent, 'Creates an inventory, project and credential directly in AAP while resolving an outage.');
  assert.equal(nodes['successor-placeholder'].hidden, true, 'The manual scene does not reveal a third destination');
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(manualItems(nodes['target-objects']).length, 3);
  for (const name of ['Emergency servers', 'Quick-fix automation', 'Temporary access']) {
    assert.ok(objectNames(nodes['target-objects']).includes(name));
    assert.ok(!nodes['config-lines'].textContent.includes(name), 'Direct UI changes have not reached Git');
  }
  nodes.next.click();
  checkReservedLayout();
  assert.equal(nodes['manual-operator'].hidden, true, 'The scan is a separate action after the operator changes');
  assert.match(nodes['config-lines'].textContent, /Emergency servers/);
  nodes.previous.click();
  checkReservedLayout();
  assert.equal(nodes['manual-operator'].hidden, false, 'Reversal returns to incident response');
  assert.doesNotMatch(nodes['config-lines'].textContent, /Emergency servers/);
  nodes.restart.click();
  checkReservedLayout();
  assert.equal(nodes['manual-operator'].hidden, true);
  assert.equal(nodes['manual-operator'].attributes['aria-hidden'], 'true');
});


test('each AAP keeps the complete infrastructure group inside its RHEL foundation', () => {
  const html = source('index.html');
  for (const prefix of ['source', 'target', 'successor']) {
    const id = `${prefix}-rhel`;
    const opening = html.match(new RegExp(`<section\\b[^>]*\\bid="${id}"[^>]*>`));
    assert.ok(opening, `${id} is a RHEL section`);
    let depth = 0;
    let foundation = '';
    for (const tag of html.slice(opening.index).matchAll(/<\/?section\b[^>]*>/gi)) {
      depth += tag[0].startsWith('</') ? -1 : 1;
      if (depth === 0) {
        foundation = html.slice(opening.index, opening.index + tag.index + tag[0].length);
        break;
      }
    }
    assert.ok(foundation, `${id} has a matching close`);
    assert.match(foundation, new RegExp(`\\bid="${prefix}-infrastructure"`), 'Infrastructure belongs within RHEL, not the AAP object catalogue');
    assert.equal((html.match(new RegExp(`\\bid="${prefix}-infrastructure"`, 'g')) || []).length, 1, 'The group is moved rather than duplicated');
  }
});
