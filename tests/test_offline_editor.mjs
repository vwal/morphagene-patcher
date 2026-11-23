// Optional browser integration test. Install Playwright and its Chromium, or
// point PLAYWRIGHT_CHROMIUM_EXECUTABLE at an existing Chromium executable.
// Run with: node tests/test_offline_editor.mjs
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {copyFile, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const {chromium} = createRequire(import.meta.url)('playwright');
const name = 'morphagene-options-editor.html';
const site = await readFile(new URL('../web/index.html', import.meta.url), 'utf8');
const expectedFields = [...site.matchAll(/\bid="(opt-[^"]+)"/g)].map(m => m[1]).sort();
assert.ok(expectedFields.includes('opt-dryk'));
assert.ok(expectedFields.includes('opt-dlen'));
const link = (site.match(/<a\b[^>]*>/gi) || []).find(tag =>
  /\shref="(?:\.\/)?morphagene-options-editor\.html"/.test(tag) && /\sdownload\b/.test(tag));
assert.ok(link, 'The patcher offers the standalone HTML as a download');

async function editStockSettings(page) {
  const headers = page.locator('.option-header');
  assert.equal(await headers.count(), 44);
  const origins = await headers.locator('.option-origin').allTextContents();
  assert.equal(origins.filter(origin => origin === 'Stock').length, 12);
  assert.equal(origins.filter(origin => origin === 'Enhancement').length, 32);
  const optional = await headers.locator('.optional-marker').allTextContents();
  assert.deepEqual(optional, Array(13).fill('OPTIONAL:'));

  const inop = page.locator('#opt-inop');
  assert.equal(await inop.inputValue(), '');
  assert.equal(await page.locator('#opt-mcr1').inputValue(), '2');
  assert.equal(await page.locator('#opt-mcr3').inputValue(), '+1.23456789');
  assert.equal(await page.locator('#opt-mcr2').inputValue(), '');
  assert.equal(await page.locator('#opt-mcr2').getAttribute('placeholder'), 'Omitted (stock default 1.5)');
  assert.doesNotMatch(await page.locator('#options-text').inputValue(), /^inop |^mcr2 /m);
  await inop.selectOption('0');
  assert.match(await page.locator('#options-text').inputValue(), /^inop 0 /m);
  await inop.selectOption('1');
  await page.locator('#opt-pmod').selectOption('2');
  const ratio = page.locator('#opt-mcr2');
  await ratio.fill('1.0');
  await ratio.press('5');
  assert.equal(await ratio.inputValue(), '1.05');
  await ratio.fill('0');
  assert.equal(await ratio.getAttribute('aria-invalid'), 'true');
  assert.equal(await page.locator('#error-mcr2').isVisible(), true);
  assert.equal(await page.locator('#options-save').isDisabled(), true);
  await ratio.fill('-0.06250000');
  await ratio.press('Tab');
  assert.equal(await ratio.inputValue(), '-0.0625');
  assert.equal(await page.locator('#options-save').isEnabled(), true);
  assert.equal(await page.locator('#error-mcr2').isVisible(), false);
  assert.match(await page.locator('#options-text').inputValue(), /^mcr2 -0\.06250000 /m);
}

async function checkReset(page) {
  const reset = page.getByRole('button', {name: 'Reset to defaults', exact: true});
  const dialog = page.getByRole('dialog', {name: 'Reset all editor settings?'});
  const preview = page.locator('#options-text');
  const before = await preview.inputValue();
  await reset.click();
  assert.equal(await dialog.getByRole('button', {name: 'Cancel'}).evaluate(el => el === document.activeElement), true);
  await page.keyboard.press('Escape');
  assert.equal(await preview.inputValue(), before);
  await reset.click();
  await dialog.getByRole('button', {name: 'Cancel'}).click();
  assert.equal(await preview.inputValue(), before);

  await page.locator('#opt-mcr1').fill('0');
  assert.equal(await page.locator('#options-save').isDisabled(), true);
  await reset.click();
  await dialog.getByRole('button', {name: 'Reset to defaults'}).click();
  assert.equal(await dialog.count(), 0);
  assert.equal(await page.locator('#options-save').isEnabled(), true);
  const result = await preview.inputValue();
  assert.ok(result.startsWith('7 45875 0\n'));
  assert.ok(result.includes('future_setting 12 // preserve me\n'));
  assert.ok(result.includes('// annotated performance reel\n'));
  assert.ok(result.includes('mcr1 2 // stock chord\n'));
  const {fields} = JSON.parse(await readFile(new URL('../web/site-content.json', import.meta.url), 'utf8'));
  const controls = await page.locator('[id^="opt-"]').evaluateAll(nodes =>
    Object.fromEntries(nodes.map(el => [el.id.slice(4), el.value])));
  const checked = await page.locator('[id^="recall-"]').evaluateAll(nodes =>
    Object.fromEntries(nodes.map(el => [el.id.slice(7), el.checked])));
  for (const [key,,,,defaultValue] of fields) {
    assert.equal(controls[key], defaultValue, key);
    if (key in checked) assert.equal(checked[key], key === 'dstr', key);
    const entry = result.split('\n').find(line => line.startsWith(key+' '));
    if (checked[key] === false) assert.equal(entry, undefined, key);
    else assert.equal(entry?.split(/\s+/)[1], defaultValue, key);
  }
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#options-save').click()]);
  assert.equal(await readFile(await download.path(), 'utf8'), result);
}

const card = await mkdtemp(path.join(tmpdir(), 'morphagene-card-'));
let browser, server;
try {
  const standalone = path.join(card, name);
  await copyFile(new URL('../web/' + name, import.meta.url), standalone);
  const url = pathToFileURL(standalone).href;
  browser = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
  const context = await browser.newContext({offline: true, acceptDownloads: true, colorScheme: 'light'});
  const page = await context.newPage();
  const unexpectedRequests = [];
  const errors = [];
  page.on('request', r => {
    if (r.url() !== url && !/^(?:data|blob):/.test(r.url())) unexpectedRequests.push(r.url());
  });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(url);
  assert.deepEqual(await page.locator('#opt-mcr1, #opt-mcr2, #opt-mcr3')
    .evaluateAll(inputs => inputs.map(input => input.value)), ['2', '1.5', '1.33333']);
  assert.equal(await page.evaluate(() => navigator.onLine), false);
  const fields = await page.locator('[id^="opt-"]').evaluateAll(nodes => nodes.map(n => n.id).sort());
  assert.deepEqual(fields, expectedFields);
  assert.equal(await page.locator('#firmware, #build-wav, #build-card').count(), 0);
  assert.equal(await page.locator('#options-save').isVisible(), false);
  const initialSnippet = await page.locator('#options-text').inputValue();
  await page.locator('#opt-vsop').selectOption('2');
  await page.locator('#recall-dstr').uncheck();
  await page.locator('#options-reset').click();
  await page.locator('#reset-confirm').click();
  assert.equal(await page.locator('#options-text').inputValue(), initialSnippet);
  assert.equal(await page.locator('#options-save').isVisible(), false);
  const theme = page.locator('#theme-toggle');
  await theme.click();
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
  assert.equal(await theme.getAttribute('aria-checked'), 'true');

  const imported = [
    '7 45875 0', '// firmware version 204', '// annotated performance reel',
    'future_setting 12 // preserve me', 'mcr1 2.00000 // stock chord',
    'mcr3 +1.23456789 // tuning',
    'vsop 1', 'dryk 0 // send', 'mpos 19 // starting position', 'dstr 7.5', ''
  ].join('\r\n');
  const input = page.locator('#options-file');
  const cardOptions = path.join(card, 'options.txt');
  await writeFile(cardOptions, imported);
  const dropZone = page.locator('#options-drop');
  await dropZone.drop({files: cardOptions});
  await page.waitForFunction(() => document.getElementById('recall-mpos').checked);
  assert.match(await page.locator('#options-status').textContent(), /Loaded options\.txt/);
  assert.equal(await page.locator('#opt-mpos').inputValue(), '19');
  await editStockSettings(page);
  await page.locator('#opt-dryk').selectOption('2');
  await page.locator('#opt-dlen').selectOption('1');
  await page.locator('#recall-dstr').uncheck();
  await page.locator('#recall-vpos').check();
  await page.locator('#opt-vpos').fill('51');
  await page.locator('#opt-vpos').press('Tab');
  const beforeMultiple = await page.locator('#options-text').inputValue();
  await dropZone.drop({files: [cardOptions, cardOptions]});
  assert.match(await page.locator('#options-status').textContent(), /single options\.txt/);
  assert.equal(await page.locator('#options-text').inputValue(), beforeMultiple);

  const [download] = await Promise.all([
    page.waitForEvent('download'), page.locator('#options-save').click()
  ]);
  assert.equal(download.suggestedFilename(), 'options.txt');
  const savedPath = await download.path();
  const saved = await readFile(savedPath, 'utf8');
  assert.equal(await readFile(cardOptions, 'utf8'), imported);
  const lines = saved.split(/\r?\n/);
  assert.equal(lines[0], '7 45875 0');
  assert.equal(lines.filter(l => /^\/\/ firmware version /.test(l)).length, 1);
  for (const line of ['// annotated performance reel', 'future_setting 12 // preserve me',
                      'mcr1 2.00000 // stock chord', 'vsop 1', 'dryk 2 // send', 'mpos 19 // starting position']) {
    assert.ok(lines.includes(line), line);
  }
  assert.match(saved, /^dlen 1(?:\s|$)/m);
  assert.match(saved, /^inop 1 /m);
  assert.match(saved, /^pmod 2 /m);
  assert.match(saved, /^mcr2 -0\.06250000 /m);
  assert.match(saved, /^mcr3 \+1\.23456789 \/\/ tuning$/m);
  assert.match(saved, /^vpos 51(?:\s|$)/m);
  assert.doesNotMatch(saved, /^dstr\s/m);
  assert.equal(await page.locator('#options-text').inputValue(), saved);

  await dropZone.drop({files: {name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('7 45875 0\n\0bad card text')}});
  await page.waitForFunction(() => document.getElementById('options-status').dataset.kind === 'error');
  assert.equal(await page.locator('#options-save').isVisible(), false);
  await input.focus();
  const [chooser] = await Promise.all([page.waitForEvent('filechooser'), input.press('Enter')]);
  await chooser.setFiles(savedPath);
  await page.locator('#options-save').waitFor({state: 'visible'});
  assert.equal(await page.locator('#opt-dryk').inputValue(), '2');
  assert.equal(await page.locator('#opt-mcr2').inputValue(), '-0.0625');
  assert.equal(await page.locator('#opt-dlen').inputValue(), '1');
  assert.equal(await page.locator('#recall-dstr').isChecked(), false);
  assert.equal(await page.locator('#recall-vpos').isChecked(), true);
  assert.equal(await page.locator('#options-text').inputValue(), saved);
  for (const width of [375, 320]) {
    await page.setViewportSize({width, height: 720});
    const contentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(contentWidth <= width, `Editor overflows ${width}px by ${contentWidth - width}px`);
  }
  await checkReset(page);
  assert.equal(await readFile(cardOptions, 'utf8'), imported);
  assert.deepEqual(unexpectedRequests, []);
  assert.deepEqual(errors, []);

  console.log(`PASS isolated file:// editor with network offline: ${fields.length} controls, theme, mobile widths, options.txt download, error recovery, and re-import`);

  // A real same-origin HTTP response exercises the browser download manager.
  const types = {html:'text/html', js:'text/javascript', css:'text/css'};
  server = createServer(async (req, res) => {
    const match = /^\/morphagene-patcher\/(?:([\w.-]+\.(html|js|css)))?$/.exec(req.url);
    if (match) {
      try {
        const bytes = await readFile(path.join(import.meta.dirname, '../web', match[1] || 'index.html'));
        res.writeHead(200, {'Content-Type': types[match[2] || 'html']}).end(bytes);
        return;
      } catch { /* Missing asset */ }
    }
    res.writeHead(404).end();
  });
  await new Promise((resolve, reject) => server.once('error', reject).listen(0, '127.0.0.1', resolve));
  const siteUrl = 'http://127.0.0.1:'+server.address().port+'/morphagene-patcher/';
  const hosted = await browser.newContext({acceptDownloads: true});
  const web = await hosted.newPage();
  web.on('pageerror', e => errors.push(e.message));
  await web.goto(siteUrl+'#options');
  const [editorDownload] = await Promise.all([
    web.waitForEvent('download'), web.getByRole('link', {name: 'Download the offline options editor'}).click()
  ]);
  assert.equal(editorDownload.suggestedFilename(), name);
  assert.deepEqual(await readFile(await editorDownload.path()), await readFile(standalone));
  assert.equal(web.url(), siteUrl+'#options');
  const firmwareZone = web.locator('#firmware-drop');
  await firmwareZone.drop({files: cardOptions});
  await web.locator('#firmware-status[data-kind="error"]').waitFor();
  assert.equal(await web.locator('#build-buttons').isVisible(), false);
  if (process.env.MGMOD_WAV) {
    await firmwareZone.drop({files: process.env.MGMOD_WAV});
    await web.locator('#firmware-status[data-kind="ok"]').waitFor();
    assert.equal(await web.locator('#build-wav').isVisible(), true);
    const [cardBuild] = await Promise.all([web.waitForEvent('download'), web.locator('#build-card').click()]);
    const bytes = await readFile(await cardBuild.path());
    const {raw_image_sha256} = JSON.parse(await readFile(new URL('../web/release.json', import.meta.url), 'utf8'));
    assert.equal(cardBuild.suggestedFilename(), 'mgmod.bin');
    assert.equal(createHash('sha256').update(bytes.subarray(0, -12)).digest('hex'), raw_image_sha256);
    await firmwareZone.drop({files: [cardOptions, cardOptions]});
    assert.equal(await web.locator('#build-buttons').isVisible(), false);
    assert.match(await web.locator('#firmware-status').textContent(), /single official mg204.wav/);
    await web.locator('#firmware').setInputFiles(process.env.MGMOD_WAV);
    await web.locator('#firmware-status[data-kind="ok"]').waitFor();
    console.log('PASS official firmware WAV drop, reference SD download, multiple-file rejection and picker recovery');
  }
  await web.locator('#options-drop').drop({files: cardOptions});
  await web.waitForFunction(() => document.getElementById('recall-mpos').checked);
  await editStockSettings(web);
  const [webDownload] = await Promise.all([web.waitForEvent('download'), web.locator('#options-save').click()]);
  const webPath = await webDownload.path();
  const webSaved = await readFile(webPath, 'utf8');
  assert.match(webSaved, /^mcr1 2\.00000 \/\/ stock chord$/m);
  assert.match(webSaved, /^mcr2 -0\.06250000 /m);
  assert.match(webSaved, /^inop 1 /m);
  assert.match(webSaved, /^pmod 2 /m);
  await web.reload();
  await web.locator('#options-file').setInputFiles(webPath);
  await web.waitForFunction(() => document.getElementById('recall-mpos').checked);
  assert.equal(await web.locator('#options-text').inputValue(), webSaved);
  await checkReset(web);
  assert.deepEqual(errors, []);
  console.log('PASS hosted and offline reset: cancel, confirm, every stock and enhancement default, optional recalls and saved card metadata');
} finally {
  await browser?.close();
  if (server?.listening) await new Promise(resolve => server.close(resolve));
  await rm(card, {recursive: true, force: true});
}
