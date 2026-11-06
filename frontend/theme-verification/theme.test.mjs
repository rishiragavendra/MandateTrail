import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const layout = readFileSync(new URL('../app/layout.tsx', import.meta.url), 'utf8');
const bootstrap = layout.match(/const themeBootstrap = `([^`]+)`;/)?.[1];
assert.ok(bootstrap, 'Pre-paint bootstrap is present in the root layout');
for (const [name, stored, expected] of [
  ['first visit defaults to Orbital dark', null, 'dark'],
  ['saved light applies before hydration', 'light', 'light'],
  ['saved dark applies before hydration', 'dark', 'dark'],
  ['invalid storage fails safely to dark', 'unexpected', 'dark'],
]) {
  test(name, () => {
    const document = { documentElement: { dataset: {} } };
    runInNewContext(bootstrap, { document, localStorage: { getItem(key) {
      assert.equal(key, 'mandatetrail-theme'); return stored;
    } } });
    assert.equal(document.documentElement.dataset.theme, expected);
  });
}
test('blocked browser storage still renders dark', () => {
  const document = { documentElement: { dataset: {} } };
  runInNewContext(bootstrap, { document, localStorage: { getItem() { throw new Error('Storage blocked'); } } });
  assert.equal(document.documentElement.dataset.theme, 'dark');
});
test('all application CSS color tokens resolve to declared theme variables', () => {
  const theme = readFileSync(new URL('../app/themes.css', import.meta.url), 'utf8');
  const css = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');
  const declared = new Set([...`${theme}\n${css}`.matchAll(/(--[\w-]+)\s*:/g)].map(m => m[1]));
  for (const file of ['../app/globals.css','../app/themes.css','../app/page.tsx','../components/provenance.tsx']) {
    for (const [,variable] of readFileSync(new URL(file,import.meta.url),'utf8').matchAll(/var\((--[\w-]+)\)/g)) {
      assert.ok(declared.has(variable), `${file}: ${variable} is undeclared`);
    }
  }
  assert.match(theme, /--background:\s*#DCE3EF/i);
  assert.match(theme, /--primary:\s*#315DCE/i);
});
