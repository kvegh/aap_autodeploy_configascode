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
const futureRoutes = ['flow-apply', 'flow-scan', 'flow-return'];

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.handlers = {};
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

test('the six chapters cover the four deployment stages and link to existing source', () => {
  assert.equal(story.chapters.length, 6);
  assert.equal(story.steps.length, 9);
  assert.deepEqual(story.steps.slice(1, 5).map(step => step.stage), [1, 2, 3, 4]);
  assert.equal(new Set(story.steps.map(step => step.id)).size, 9);
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
  assert.ok(!objectNames(nodes['target-objects']).includes('Regional servers'));
  assert.ok(!nodes['config-lines'].textContent.includes('Regional servers'));
  nodes.restart.click();
  assert.equal(nodes['step-count'].textContent, '1 / 9');
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
  for (let index = 0; index < 9; index++) {
    assert.equal(nodes['step-count'].textContent, `${index + 1} / 9`);
    assert.equal(nodes['chapter-list'].children.filter(item => item.attributes['aria-current'] === 'step').length, 1);
    nodes.next.click();
  }
  assert.equal(nodes.next.disabled, true);
  page.key('ArrowRight');
  assert.equal(nodes['step-count'].textContent, '9 / 9');
  page.key('ArrowLeft');
  assert.equal(nodes['step-count'].textContent, '8 / 9');
  page.key('r');
  assert.equal(nodes['step-count'].textContent, '1 / 9');
  page.key('ArrowLeft');
  assert.equal(nodes['step-count'].textContent, '1 / 9');
  page.key('ArrowRight', { target: new Element('input') });
  page.key('ArrowRight', { ctrlKey: true });
  assert.equal(nodes['step-count'].textContent, '1 / 9');
  assert.equal(page.key('ArrowRight').prevented, true);
  assert.equal(nodes['step-count'].textContent, '2 / 9');
});

test('direct links and later hash changes restore the complete scene state', () => {
  for (const [index, step] of story.steps.entries()) {
    const page = browser(`#${step.id}`);
    assert.equal(page.nodes['step-count'].textContent, `${index + 1} / 9`);
    assert.equal(page.nodes['scene-title'].textContent, step.title);
    assert.equal(objectNames(page.nodes['target-objects']).length, story.stateAt(index).targetObjects.length);
  }
  const page = browser('#unrecognized');
  assert.equal(page.nodes['step-count'].textContent, '1 / 9');
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
  assert.equal(story.stateAt(8).targetObjects.filter(item => item.origin === 'manual' && item.inGit).length, 3);
  assert.equal(story.stateAt(7).targetObjects.filter(item => item.origin === 'manual' && item.inGit).length, 0);
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
    ['git-change', 'Apply objects', 'New AAP', ['flow-config', 'flow-code', 'flow-apply']],
    ['manual', null, null, []],
    ['capture', null, null, ['flow-scan', 'flow-return']],
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
