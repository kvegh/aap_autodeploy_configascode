'use strict';

const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const scenario = require('../src/scenario.js');

const demo = path.resolve(__dirname, '..');
const html = readFileSync(path.join(demo, 'index.html'), 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.handlers = {};
    this.style = {};
    this.dataset = {};
    this.disabled = false;
    this.textContent = '';
    this.classes = new Set();
    this.classList = { toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name) };
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(name, callback) { this.handlers[name] = callback; }
  querySelector(name) { if (name === 'small') return this.small; throw new Error(`Unexpected selector: ${name}`); }
  closest() { return null; }
  click() { if (!this.disabled) this.handlers.click?.(); }
}

function browser({ hash = '', reduced = false } = {}) {
  const nodes = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  nodes.next.small = new Element('small');
  const app = new Element();
  const media = { matches: reduced, addEventListener: (name, callback) => { media.change = callback; } };
  const document = {
    handlers: {},
    getElementById: id => { assert.ok(nodes[id], `Missing actual HTML element ${id}`); return nodes[id]; },
    querySelector: selector => { assert.equal(selector, '.app'); return app; },
    createElement: tag => new Element(tag),
    addEventListener(name, callback) { this.handlers[name] = callback; },
  };
  const location = { hash };
  const context = vm.createContext({ document, location, matchMedia: () => media,
    history: { replaceState: (state, unused, next) => { location.hash = next; } },
    addEventListener: (name, callback) => { context[name] = callback; },
  });
  context.window = context;
  vm.runInContext(readFileSync(path.join(demo, 'src/scenario.js'), 'utf8'), context);
  vm.runInContext(readFileSync(path.join(demo, 'src/app.js'), 'utf8'), context);
  return { nodes, app, document, context, media,
    key(key, extra = {}) {
      const event = { key, target: new Element(), preventDefault() { this.prevented = true; }, ...extra };
      document.handlers.keydown(event);
      return event;
    },
  };
}

test('the page and source citations resolve to actual assets and reviewed repository files', () => {
  for (const asset of [...html.matchAll(/(?:href|src)="([^"#]+\.(?:css|js|svg))"/g)]) {
    assert.ok(existsSync(path.join(demo, asset[1])), `Missing page asset: ${asset[1]}`);
  }
  for (const step of scenario.steps) {
    for (const source of step.sources) assert.ok(existsSync(path.join(demo, '..', source)), `Missing code citation: ${source}`);
  }
  assert.match(scenario.sourceRevision, /^[0-9a-f]{40}$/);
  assert.equal(scenario.runtimeVersion, '0.50.13');
  assert.equal(new Set(scenario.steps.map(step => step.id)).size, scenario.steps.length);
  assert.equal(scenario.steps.length, 12);
  assert.throws(() => scenario.stepAt('1'), TypeError);
  assert.throws(() => scenario.move(0, 8), TypeError);
});

test('next and previous reveal and remove the correct configuration groups', () => {
  const { nodes } = browser();
  assert.equal(nodes.previous.disabled, true);
  assert.equal(nodes.progress.attributes['aria-valuenow'], '1');
  for (let i = 0; i < scenario.steps.length; i++) {
    assert.equal(nodes['current-title'].textContent, scenario.steps[i].title);
    assert.equal(nodes['resource-base'].classes.has('configured'), i >= scenario.steps.findIndex(step => step.id === 'base'));
    assert.equal(nodes['resource-templates'].classes.has('configured'), i >= scenario.steps.findIndex(step => step.id === 'import'));
    const active = nodes['step-list'].children.filter(item => item.children[0].attributes['aria-current'] === 'step');
    assert.equal(active.length, 1);
    if (i < scenario.steps.length - 1) nodes.next.click();
  }
  nodes.previous.click();
  assert.equal(nodes['current-title'].textContent, scenario.steps.at(-2).title);
  for (let i = 0; i < 20; i++) nodes.previous.click();
  assert.equal(nodes.progress.attributes['aria-valuenow'], '1');
  assert.equal(nodes['resource-base'].classes.has('configured'), false);
  assert.equal(nodes['route-apply'].classes.has('active'), false);
});

test('the same-instance choice changes roles without pretending to create another platform', () => {
  const { nodes, context } = browser({ hash: '#destination' });
  nodes['target-self'].click();
  assert.equal(nodes['target-self'].attributes['aria-pressed'], 'true');
  assert.match(nodes['target-role'].textContent, /same verified AAP/);
  assert.match(nodes['target-explanation'].textContent, /two roles in the flow/);
  assert.equal(context.location.hash, '#destination');
  nodes.restart.click();
  assert.equal(nodes.progress.attributes['aria-valuenow'], '1');
  assert.equal(nodes['target-remote'].attributes['aria-pressed'], 'true');
});

test('direct links, keyboard navigation, restart and the final next button stay coherent', () => {
  const view = browser({ hash: '#capture' });
  assert.equal(view.nodes['node-review'].classes.has('active'), true);
  assert.equal(view.nodes['route-review'].classes.has('active'), true);
  view.context.location.hash = '#walkthrough';
  view.context.hashchange();
  assert.equal(view.nodes['current-title'].textContent, scenario.steps.find(step => step.id === 'capture').title);
  assert.equal(view.key('ArrowRight').prevented, true);
  assert.equal(view.context.location.hash, '#complete');
  view.key('ArrowLeft', { ctrlKey: true });
  assert.equal(view.context.location.hash, '#complete');
  view.nodes.next.click();
  assert.equal(view.context.location.hash, '#overview');
  view.key('ArrowLeft');
  assert.equal(view.context.location.hash, '#overview');
  view.nodes.next.click();
  view.key('r');
  assert.equal(view.context.location.hash, '#overview');
  assert.equal(browser({ hash: '#not-a-step' }).nodes.progress.attributes['aria-valuenow'], '1');
});

test('reduced-motion preference and its changes are honored', () => {
  const view = browser({ reduced: true });
  assert.equal(view.app.dataset.motion, 'off');
  assert.equal(view.nodes.motion.attributes['aria-pressed'], 'false');
  view.media.change({ matches: false });
  assert.equal(view.app.dataset.motion, 'on');
  view.nodes.motion.click();
  assert.equal(view.app.dataset.motion, 'off');
});

test('the four actual stages select the correct diagram, route, result and phase', () => {
  const { nodes, app } = browser();
  nodes['stage-vm'].click();
  assert.equal(app.dataset.view, 'deployment');
  assert.equal(nodes['deployment-view'].hidden, false);
  assert.equal(nodes['configuration-view'].hidden, true);
  assert.equal(nodes['target-controls'].hidden, true);
  assert.equal(nodes['deployment-context'].hidden, false);
  assert.match(nodes.phase.textContent, /Stage 01/);
  assert.equal(nodes['deploy-state'].classes.has('ready'), true);
  assert.equal(nodes['deploy-guest'].classes.has('ready'), true);
  assert.equal(nodes['deploy-route-reserve'].classes.has('active'), true);
  assert.equal(nodes['deploy-route-copy'].classes.has('active'), true);
  assert.equal(nodes['deploy-platform'].classes.has('ready'), false);
  nodes['stage-infrastructure'].click();
  assert.match(nodes.phase.textContent, /Stage 02/);
  assert.equal(nodes['deploy-edge'].classes.has('active'), true);
  assert.equal(nodes['deploy-route-dns'].classes.has('active'), true);
  assert.equal(nodes['deploy-route-copy'].classes.has('active'), false);
  assert.match(nodes['edge-status'].textContent, /upstream pending/);
  nodes.next.click();
  assert.match(nodes.phase.textContent, /Stage 03/);
  assert.equal(nodes['deploy-platform'].classes.has('ready'), true);
  assert.equal(nodes['deploy-route-install'].classes.has('active'), true);
  assert.match(nodes['platform-status'].textContent, /verified/);
  nodes.next.click();
  assert.match(nodes.phase.textContent, /Stage 04/);
  assert.equal(app.dataset.view, 'configuration');
  assert.equal(nodes['deployment-view'].hidden, true);
  assert.equal(nodes['configuration-view'].hidden, false);
  assert.equal(nodes['target-controls'].hidden, false);
  assert.equal(nodes['resource-base'].classes.has('configured'), true);
  assert.equal(nodes['resource-templates'].classes.has('configured'), false);
  assert.equal(nodes['stage-base'].attributes['aria-current'], 'step');
  assert.equal(nodes['stage-installation'].dataset.state, 'complete');
  nodes.previous.click();
  nodes.previous.click();
  assert.equal(nodes['deploy-platform'].classes.has('ready'), false);
  assert.equal(nodes['deploy-route-install'].classes.has('active'), false);
  assert.match(nodes['edge-status'].textContent, /upstream pending/);
  nodes.restart.click();
  assert.equal(app.dataset.view, 'configuration');
  assert.equal(nodes['deploy-route-dns'].classes.has('active'), false);
  assert.equal(nodes['stage-vm'].dataset.state, 'pending');
  assert.equal(nodes.progress.attributes['aria-valuemax'], '12');
});

test('deployment direct links work and the complete palette uses blue or neutral hues', () => {
  const view = browser({ hash: '#installation' });
  assert.equal(view.app.dataset.view, 'deployment');
  assert.equal(view.nodes['stage-installation'].attributes['aria-current'], 'step');
  const css = readFileSync(path.join(demo, 'src/styles.css'), 'utf8');
  const icon = readFileSync(path.join(demo, 'icon.svg'), 'utf8');
  assert.doesNotMatch(css, /--teal|--red/);
  assert.match(css, /--blue: #1767bd/);
  for (const match of (css + html + icon).matchAll(/#([0-9a-f]{6})(?:[0-9a-f]{2})?\b/gi)) {
    const red = parseInt(match[1].slice(0, 2), 16);
    const green = parseInt(match[1].slice(2, 4), 16);
    const blue = parseInt(match[1].slice(4, 6), 16);
    assert.ok(blue >= green && blue >= red, `Non-blue color remains: ${match[0]}`);
  }
});

test('all code examples are inserted as text and source links stay on the pinned public checkout', () => {
  const { nodes } = browser();
  for (let i = 0; i < scenario.steps.length; i++) {
    assert.equal(nodes['code-example'].textContent, scenario.steps[i].code);
    for (const item of nodes['source-links'].children) {
      assert.ok(item.children[0].href.startsWith(scenario.sourceRoot));
      assert.equal(item.children[0].rel, 'noopener noreferrer');
    }
    nodes.next.click();
  }
  const script = readFileSync(path.join(demo, 'src/app.js'), 'utf8');
  assert.doesNotMatch(script, /innerHTML|\bfetch\s*\(|XMLHttpRequest|WebSocket/);
});
