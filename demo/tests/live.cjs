'use strict';
// Test the deployed static assets with existing interaction checks. See ../README.md#verification.
const { mkdtemp, mkdir, readFile, writeFile, rm } = require('node:fs/promises');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const assets = ['index.html', 'icon.svg', 'src/app.js', 'src/scenario.js', 'src/styles.css'];
const defaultUrl = 'https://kvegh.github.io/aap_autodeploy_configascode/';
const maximumAssetBytes = 1024 * 1024;

async function download(base, asset, directory) {
  const response = await fetch(new URL(asset, base), {
    redirect: 'error', signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const chunks = [];
  let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > maximumAssetBytes) throw new Error('Asset exceeds the 1 MiB check limit');
    chunks.push(chunk);
  }
  await writeFile(path.join(directory, asset), Buffer.concat(chunks));
}

async function main() {
  if (process.argv.length > 3) throw new Error('Usage: node demo/tests/live.cjs [https://site.example/path/]');
  const base = new URL(process.argv[2] || defaultUrl);
  if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash) {
    throw new Error('Supply an HTTPS site-directory URL without credentials, query or fragment');
  }
  if (!base.pathname.endsWith('/')) base.pathname += '/';
  const directory = await mkdtemp(path.join(tmpdir(), 'aap-cac-live-'));
  try {
    await mkdir(path.join(directory, 'src'));
    const results = await Promise.allSettled(assets.map(asset => download(base, asset, directory)));
    const failures = results.flatMap((result, index) => result.status === 'rejected'
      ? [`${assets[index]}: ${result.reason.message}`] : []);
    if (failures.length) throw new Error(`Live asset download failed: ${failures.join('; ')}`);
    for (const asset of assets) {
      const published = await readFile(path.join(directory, asset));
      const checkedOut = await readFile(path.resolve(__dirname, '..', asset));
      if (!published.equals(checkedOut)) throw new Error(`Published asset differs from this checkout: ${asset}`);
    }
    console.log(`PASS: five published assets match this checkout at ${base.href}`);
    console.log('Checking real deployed HTML/JavaScript interactions; browser layout is outside this check.');
    const result = spawnSync(process.execPath, ['--test', path.join(__dirname, 'walkthrough.test.cjs')], {
      env: { ...process.env, AAP_CAC_DEMO_DIR: directory }, stdio: 'inherit', timeout: 30000,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Live interaction tests failed (${result.signal || result.status})`);
    console.log('PASS: deployed visualization interactions.');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(`FAIL: ${error.message}`);
  process.exitCode = 1;
});
