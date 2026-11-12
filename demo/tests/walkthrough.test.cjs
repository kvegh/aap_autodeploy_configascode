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
  append(...nodes) { nodes.forEach(node => { node.parentElement = this; this.children.push(node); }); }
  replaceChildren(...nodes) { this.children = []; this.ownText = ''; this.append(...nodes); }
  addEventListener(name, callback) { (this.handlers[name] ||= []).push(callback); }
  scrollIntoView(options) { this.scrollRequests.push(options); }
  click() { if (!this.disabled) (this.handlers.click || []).forEach(callback => callback({ target: this })); }
  querySelectorAll(selector) {
    assert.equal(selector, '[data-stage]');
    return descendants(this).filter(node => node.dataset.stage !== undefined);
  }
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
function browser(hash = '') {
  const html = source('index.html');
  const nodes = {};
  for (const match of html.matchAll(/<([a-z][\w:-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
    assert.equal(nodes[match[3]], undefined, `Duplicate HTML ID ${match[3]}`);
    nodes[match[3]] = attributes(new Element(match[1]), match[2]);
  }
  for (const match of html.matchAll(/<button\b([^>]*\bdata-stage=(?:"[^"]+"|'[^']+')[^>]*)>/gi)) {
    const button = attributes(new Element('button'), match[1]);
    nodes['stage-list'].append(button);
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
const objectNames = node => withClass(node, 'object-name').map(item => item.textContent);
const manualItems = node => withClass(node, 'object-item').filter(item => item.dataset.origin === 'manual');

test('the seven chapters cover deployment, capture and replay with existing source links', () => {
  assert.equal(story.chapters.length, 7);
  assert.equal(story.steps.length, 11);
  assert.deepEqual(story.steps.slice(1, 5).map(step => step.stage), [1, 2, 3, 4]);
  assert.equal(new Set(story.steps.map(step => step.id)).size, 11);
  assert.equal(story.steps.find(step => step.id === 'infra-change').chapter, 'git-change');
  assert.equal(story.steps.at(-1).id, 'rebuild');
  assert.match(story.sourceRevision, /^[a-f0-9]{40}$/);
  for (const step of story.steps) {
    for (const reference of step.sources) assert.ok(existsSync(path.resolve(repository, reference)), reference);
    const code = step.sources.map(reference => readFileSync(path.resolve(repository, reference), 'utf8')).join('\n');
    const actualLines = new Set(code.split('\n').map(line => line.trim()));
    const excerpt = story.executionLines(story.stateAt(story.steps.indexOf(step)));
    if (step.id === 'capture') {
      const inputs = excerpt.filter(line => line.trim() && !line.trim().startsWith('#'));
      for (const line of inputs) {
        const match = line.match(/^(aap_cac_capture_(?:scope|mode|commit|push)):\s+(.+)$/);
        assert.ok(match, `Unknown illustrative capture input: ${line}`);
        assert.ok(code.includes(match[1]), `Capture implementation does not accept ${match[1]}`);
      }
      assert.ok(inputs.includes('aap_cac_capture_mode: update'));
      assert.ok(inputs.includes('aap_cac_capture_commit: true'));
      assert.ok(inputs.includes('aap_cac_capture_push: true'));
    } else {
      for (const line of excerpt) {
        if (line.trim() && !line.trim().startsWith('#')) assert.ok(actualLines.has(line.trim()), `Unmapped execution excerpt in ${step.id}: ${line}`);
      }
    }
  }
});

test('the actual HTML hides future objects before scripts run and uses local assets', () => {
  const html = source('index.html');
  const opening = id => { const match = html.match(new RegExp(`<[^>]*\\bid="${id}"[^>]*>`)); assert.ok(match, id); return match[0]; };
  assert.match(opening('target-card'), /\bhidden\b/);
  assert.match(opening('target-card'), /aria-hidden="true"/);
  assert.match(opening('successor-card'), /\bhidden\b/);
  assert.match(opening('successor-card'), /aria-hidden="true"/);
  assert.match(opening('target-infrastructure-panel'), /\bhidden\b/);
  assert.doesNotMatch(opening('source-card'), /\bhidden\b/);
  for (const route of futureRoutes) assert.match(opening(route), /\bhidden\b/);
  for (const route of ['flow-config', 'flow-code']) assert.doesNotMatch(opening(route), /\bhidden\b/);
  for (const match of html.matchAll(/(?:href|src)="([^"#]+\.(?:css|js|svg))"/g)) assert.ok(existsSync(path.join(demo, match[1])), match[1]);
  assert.match(source('src/styles.css'), /\[hidden\][\s\S]{0,100}display\s*:\s*none/);
});

test('the four real stage buttons reveal VM, installed AAP, then base objects', () => {
  const { nodes } = browser();
  const sourceNames = objectNames(nodes['source-objects']);
  assert.equal(nodes['target-card'].hidden, true);
  assert.equal(nodes['target-placeholder'].hidden, false);
  assert.equal(nodes['previous'].disabled, true);
  const buttons = nodes['stage-list'].querySelectorAll('[data-stage]');
  assert.equal(buttons.length, 4);
  buttons.forEach((button, index) => {
    button.click();
    assert.equal(nodes['target-card'].hidden, false);
    assert.equal(nodes['target-placeholder'].hidden, true);
    assert.equal(nodes['target-card'].attributes['aria-hidden'], 'false');
    assert.equal(nodes['target-title'].textContent, index < 2 ? 'New RHEL VM' : 'New AAP');
    assert.equal(nodes['target-objects'].hidden, index < 3);
    assert.deepEqual(objectNames(nodes['target-objects']), index < 3 ? [] : sourceNames);
    assert.equal(button.attributes['aria-current'], 'step');
    assert.equal(buttons.filter(item => item.attributes['aria-current'] === 'step').length, 1);
  });
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
  assert.equal(objectNames(nodes['target-objects']).length, 8);
  assert.ok(objectNames(nodes['target-objects']).includes('Operations'));
  assert.ok(objectNames(nodes['target-objects']).includes('Deploy application'));
  assert.equal(withClass(nodes['target-objects'], 'object-item').filter(item => item.dataset.origin === 'git').length, 4);
  assert.equal(nodes['flow-apply'].hidden, false);
});

test('CaC edits appear in YAML and the receiving catalogue without altering the source AAP', () => {
  const page = browser();
  const original = objectNames(page.nodes['source-objects']);
  page.chapter('git-change');
  const { nodes } = page;
  for (const name of ['Regional servers', 'Regional automation']) {
    assert.ok(objectNames(nodes['target-objects']).includes(name));
    assert.ok(nodes['config-lines'].textContent.includes(name));
  }
  const additions = withClass(nodes['config-lines'], 'line-added').map(line => line.textContent);
  for (const name of ['Regional servers', 'Regional automation']) {
    assert.ok(additions.some(line => line.includes(name)), `${name} must be highlighted as a new definition`);
  }
  assert.deepEqual(objectNames(nodes['source-objects']), original);
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
  assert.equal(withClass(nodes['target-objects'], 'git-badge').length, 0);
  assert.match(nodes.feedback.textContent, /not recorded in Git yet/);
  assert.equal(nodes['flow-apply'].hidden, true);
  page.chapter('capture');
  for (const item of manualItems(nodes['target-objects'])) {
    const name = withClass(item, 'object-name')[0].textContent;
    assert.ok(nodes['config-lines'].textContent.includes(name));
    assert.equal(withClass(item, 'git-badge')[0].textContent, 'In Git');
    assert.equal(withClass(item, 'origin-label')[0].textContent, 'Manual');
  }
  assert.equal(nodes['flow-scan'].hidden, false);
  assert.equal(nodes['flow-return'].hidden, false);
  assert.equal(nodes['flow-apply'].hidden, true);
  assert.equal(nodes['job-label'].textContent, 'Scan AAP configuration');
});

test('backwards navigation and restart reverse capture, manual and Git additions', () => {
  const { nodes } = browser('#capture');
  nodes.previous.click();
  assert.equal(withClass(nodes['target-objects'], 'git-badge').length, 0);
  assert.ok(!nodes['config-lines'].textContent.includes('Emergency servers'));
  nodes.previous.click();
  assert.equal(manualItems(nodes['target-objects']).length, 0);
  assert.ok(nodes['config-lines'].textContent.includes('Regional servers'));
  nodes.previous.click();
  assert.ok(objectNames(nodes['target-objects']).includes('Regional servers'), 'Git object changes precede the infrastructure substep');
  nodes.previous.click();
  assert.ok(!objectNames(nodes['target-objects']).includes('Regional servers'));
  assert.ok(!nodes['config-lines'].textContent.includes('Regional servers'));
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
    assert.equal(objectNames(page.nodes['target-objects']).length, story.stateAt(index).targetObjects.length);
  }
  const page = browser('#unrecognized');
  assert.equal(page.nodes['step-count'].textContent, `1 / ${story.steps.length}`);
  page.hash('#capture');
  assert.equal(withClass(page.nodes['target-objects'], 'git-badge').length, 3);
  page.hash('#manual');
  assert.equal(withClass(page.nodes['target-objects'], 'git-badge').length, 0);
  page.hash('#unrecognized');
  assert.equal(page.nodes['target-card'].hidden, true);
});

test('source links stay pinned and the presentation performs no network operations', () => {
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
});

test('active routes remain visible and deployment actions name the current stage', () => {
  const page = browser();
  const expected = [
    ['separation', null, null, []],
    ['vm', 'Create VM', 'New VM', ['flow-config', 'flow-code', 'flow-apply']],
    ['infrastructure', 'Prepare OS', 'New VM', ['flow-code', 'flow-apply']],
    ['installation', 'Install AAP', 'New AAP', ['flow-code', 'flow-apply']],
    ['base', 'Apply base', 'New AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['project', 'Apply objects', 'New AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['git-change', 'Apply changes', 'New AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['infra-change', 'Apply infra', 'New AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['manual', null, null, []],
    ['capture', null, null, ['flow-scan', 'flow-return']],
    ['rebuild', null, null, ['flow-config', 'flow-code', 'flow-rebuild']],
  ];
  for (const [id, caption, detail, activeRoutes] of expected) {
    page.hash(`#${id}`);
    if (caption) {
      assert.equal(page.nodes['apply-caption'].textContent, caption, id);
      assert.equal(page.nodes['apply-detail'].textContent, detail, id);
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
  for (const id of ['chapter-list', 'stage-list', 'previous', 'next', 'restart', 'step-count', 'progress-fill', 'feedback', 'legend']) {
    assert.match(sidebar, new RegExp(`\\bid="${id}"`), `${id} belongs in the sidebar`);
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
    ['base', 'base', ['Platform', 'Platform automation']],
    ['project', 'git', ['Operations', 'Application automation']],
    ['git-change', 'git', ['Regional servers', 'Regional automation']],
    ['infra-change', 'git', ['Monitoring Agent Config v2']],
    ['capture', 'manual', ['Emergency servers', 'Quick-fix automation']],
    ['vm', 'base', ['Platform']],
  ]) {
    page.hash(`#${id}`);
    const activeRoutes = ['flow-config', 'flow-code', ...futureRoutes].map(route => page.nodes[route]).filter(route => route.classList.contains('active'));
    assert.ok(activeRoutes.length > 0, id);
    for (const route of activeRoutes) assert.equal(route.dataset.origin, origin, `${id}: route origin`);
    const highlighted = withClass(page.nodes['config-lines'], 'line-active');
    assert.ok(highlighted.length > 0, `${id}: highlighted configuration`);
    for (const line of highlighted) assert.equal(line.dataset.origin, origin, `${id}: configuration origin`);
    for (const name of names) assert.ok(highlighted.some(line => line.textContent.includes(name)), `${id}: ${name}`);
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
  assert.deepEqual(names('source-configuration'), ['Logging Config v1', 'EDA Config v1']);
  assert.equal(nodes['target-configuration-panel'].hidden, true);
  for (const id of ['vm', 'infrastructure', 'installation']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-configuration-panel'].hidden, true);
    assert.deepEqual(names('target-configuration'), []);
  }
  for (const id of ['base', 'project']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-configuration-panel'].hidden, false);
    assert.deepEqual(names('target-configuration'), ['Logging Config v1', 'EDA Config v1']);
    for (const item of withClass(nodes['target-configuration'], 'configuration-item')) assert.equal(item.dataset.origin, 'base');
  }
  for (const id of ['git-change', 'infra-change', 'manual', 'capture', 'rebuild']) {
    page.hash(`#${id}`);
    assert.deepEqual(names('target-configuration'), ['Logging Config v2', 'EDA Config v1']);
    const configs = withClass(nodes['target-configuration'], 'configuration-item');
    assert.equal(configs.filter(item => item.dataset.configId === 'logging').length, 1, 'Logging is updated, not duplicated');
    assert.equal(configs.find(item => item.dataset.configId === 'logging').dataset.origin, 'git');
    assert.equal(configs.find(item => item.dataset.configId === 'eda').dataset.origin, 'base');
    assert.deepEqual(names('source-configuration'), ['Logging Config v1', 'EDA Config v1']);
    assert.match(nodes['config-lines'].textContent, /Logging Config v2/);
    assert.doesNotMatch(nodes['config-lines'].textContent, /Logging Config v1/);
  }
  page.hash('#git-change');
  assert.equal(nodes['job-label'].textContent, 'Apply configuration');
  const logging = withClass(nodes['config-lines'], 'line-active').filter(line => line.textContent.includes('LOG_AGGREGATOR_ACTION_QUEUE_SIZE'));
  assert.equal(logging.length, 1);
  assert.equal(logging[0].dataset.origin, 'git');
  assert.match(logging[0].textContent, /20000/);
  assert.ok(nodes['source-links'].children.some(link => link.href.endsWith('/04-aap-config.yml')));
  page.hash('#base');
  assert.deepEqual(names('target-configuration'), ['Logging Config v1', 'EDA Config v1']);
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
    assert.equal(nodes['successor-placeholder'].hidden, false, step.id);
    assert.deepEqual(objectNames(nodes['successor-objects']), [], step.id);
    assert.deepEqual(objectNames(nodes['successor-configuration']), [], step.id);
    assert.deepEqual(objectNames(nodes['successor-infrastructure']), [], step.id);
    assert.equal(story.stateAt(story.steps.indexOf(step)).successorVisible, false, step.id);
  }
  const captured = story.stateAt(story.steps.findIndex(step => step.id === 'capture'));
  page.chapter('rebuild');
  assert.equal(nodes['successor-card'].hidden, false);
  assert.equal(nodes['successor-card'].attributes['aria-hidden'], 'false');
  assert.equal(nodes['successor-placeholder'].hidden, true);
  assert.deepEqual(objectNames(nodes['successor-objects']).sort(), captured.configObjects.map(object => object.name).sort());
  assert.deepEqual(objectNames(nodes['successor-configuration']), ['Logging Config v2', 'EDA Config v1']);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), ['Monitoring Agent Config v2', 'Firewall Config v1']);
  const successorItems = withClass(nodes['successor-objects'], 'object-item');
  assert.equal(successorItems.length, 13);
  assert.equal(successorItems.filter(item => item.dataset.origin === 'base').length, 4);
  assert.equal(successorItems.filter(item => item.dataset.origin === 'git').length, 6);
  assert.equal(successorItems.filter(item => item.dataset.origin === 'manual').length, 3);
  assert.equal(withClass(nodes['successor-objects'], 'git-badge').length, 3);
  for (const item of manualItems(nodes['successor-objects'])) {
    assert.equal(withClass(item, 'origin-label')[0].textContent, 'Captured');
    assert.equal(withClass(item, 'git-badge')[0].textContent, 'In Git');
  }
  assert.deepEqual(objectNames(nodes['target-objects']).sort(), captured.targetObjects.map(object => object.name).sort());
  assert.deepEqual(objectNames(nodes['target-configuration']), ['Logging Config v2', 'EDA Config v1']);
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
  assert.equal(replay.targetConfiguration[0].name, 'Logging Config v2');
  assert.equal(story.stateAt(story.steps.length - 1).successorConfiguration[0].name, 'Logging Config v2');
  replay.successorInfrastructure[0].name = 'Changed infrastructure fixture';
  assert.equal(replay.targetInfrastructure[0].name, 'Monitoring Agent Config v2');
  assert.equal(story.stateAt(story.steps.length - 1).successorInfrastructure[0].name, 'Monitoring Agent Config v2');
  nodes.previous.click();
  assert.equal(nodes['successor-card'].hidden, true);
  assert.deepEqual(objectNames(nodes['successor-objects']), []);
  assert.deepEqual(objectNames(nodes['successor-configuration']), []);
  assert.deepEqual(objectNames(nodes['successor-infrastructure']), []);
  assert.equal(withClass(nodes['target-objects'], 'git-badge').length, 3, 'Captured first target is retained');
  page.chapter('rebuild');
  nodes.restart.click();
  assert.equal(nodes['successor-card'].hidden, true);
  assert.equal(nodes['successor-placeholder'].hidden, false);
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
  assert.equal(page.nodes['job-label'].textContent, 'Apply infrastructure configuration');
  assert.equal(gitChapter.scrollRequests.length, gitRequests, 'The infrastructure substep retains the current Git chapter');
  assert.equal(gitChapter.attributes['aria-current'], 'step');
});


test('infrastructure job configuration updates monitoring while retaining firewall and source revisions', () => {
  const page = browser();
  const { nodes } = page;
  const names = id => objectNames(nodes[id]);
  const original = ['Monitoring Agent Config v1', 'Firewall Config v1'];
  assert.deepEqual(names('source-infrastructure'), original);
  for (const id of ['separation', 'vm', 'infrastructure', 'installation']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-infrastructure-panel'].hidden, true, id);
    assert.deepEqual(names('target-infrastructure'), [], id);
  }
  for (const id of ['base', 'project', 'git-change']) {
    page.hash(`#${id}`);
    assert.equal(nodes['target-infrastructure-panel'].hidden, false, id);
    assert.deepEqual(names('target-infrastructure'), original, id);
    for (const item of withClass(nodes['target-infrastructure'], 'configuration-item')) assert.equal(item.dataset.origin, 'base');
  }
  for (const id of ['infra-change', 'manual', 'capture', 'rebuild']) {
    page.hash(`#${id}`);
    assert.deepEqual(names('target-infrastructure'), ['Monitoring Agent Config v2', 'Firewall Config v1'], id);
    assert.deepEqual(names('source-infrastructure'), original, id);
    const configurations = withClass(nodes['target-infrastructure'], 'configuration-item');
    assert.equal(configurations.filter(item => item.dataset.configId === 'monitoring').length, 1, 'Monitoring is replaced, not duplicated');
    assert.equal(configurations.find(item => item.dataset.configId === 'monitoring').dataset.origin, 'git');
    assert.equal(configurations.find(item => item.dataset.configId === 'firewall').dataset.origin, 'base');
    assert.match(nodes['config-lines'].textContent, /Monitoring Agent Config v2/);
    assert.doesNotMatch(nodes['config-lines'].textContent, /Monitoring Agent Config v1/);
  }
  page.hash('#infra-change');
  assert.equal(nodes['job-label'].textContent, 'Apply infrastructure configuration');
  assert.equal(nodes['apply-caption'].textContent, 'Apply infra');
  const highlighted = withClass(nodes['config-lines'], 'line-active');
  assert.ok(highlighted.some(line => /config_revision:\s*v2/.test(line.textContent)), 'Updated monitoring inputs are highlighted');
  for (const line of highlighted) assert.equal(line.dataset.origin, 'git');
  nodes.previous.click();
  assert.deepEqual(names('target-infrastructure'), original, 'Backing up restores the previous infrastructure revision');
  assert.deepEqual(names('target-configuration'), ['Logging Config v2', 'EDA Config v1'], 'The earlier logging update is retained');
  page.chapter('rebuild');
  assert.deepEqual(names('successor-infrastructure'), ['Monitoring Agent Config v2', 'Firewall Config v1']);
  nodes.restart.click();
  assert.equal(nodes['target-infrastructure-panel'].hidden, true);
  assert.deepEqual(names('target-infrastructure'), []);
  assert.deepEqual(names('successor-infrastructure'), []);
});
