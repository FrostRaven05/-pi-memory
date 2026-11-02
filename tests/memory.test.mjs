import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {memoryStore} from '../login_demo/memory/store.mjs';

test('persistent CRUD, isolation, stale sources and exact revisions', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'homework-memory-'));
  const other = fs.mkdtempSync(path.join(os.tmpdir(), 'homework-other-'));
  fs.writeFileSync(path.join(root, 'source.md'), 'original');
  const store = memoryStore(root);
  const p = {id:'session', title:'会话', content:'测试入口', sources:['source.md']};
  assert.equal(store.write(p).record.revision, 1);
  assert.throws(() => store.write(p), /already exists/);
  assert.equal(memoryStore(other).search('').records.length, 0);
  const moduleUrl = new URL('../login_demo/memory/store.mjs', import.meta.url).href;
  const child = spawnSync(process.execPath, ['--input-type=module','-e', `import {memoryStore} from ${JSON.stringify(moduleUrl)}; console.log(memoryStore(process.argv[1]).read('session').record.revision)`, root], {encoding:'utf8'});
  assert.equal(child.status, 0); assert.equal(child.stdout.trim(), '1');
  assert.throws(() => store.update({...p, expected_revision:9}), /Revision conflict/);
  fs.writeFileSync(path.join(root, 'source.md'), 'changed');
  assert.equal(store.read('session').source_checks[0].unchanged, false);
  assert.equal(store.update({...p, expected_revision:1}).record.revision, 2);
  assert.equal(store.read('session').source_checks[0].unchanged, true);
  assert.throws(() => store.write({...p, id:'escape', sources:['../outside']}), /Invalid source/);
  store.delete('session', 2); assert.equal(store.search('').records.length, 0);
  assert.throws(() => store.read('session'), /not found/);
});
