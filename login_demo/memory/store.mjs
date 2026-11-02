import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const digest = (s) => crypto.createHash('sha256').update(s).digest('hex');
const validId = (id) => typeof id === 'string' && /^[a-z0-9][a-z0-9_-]{0,79}$/.test(id);
export function memoryStore(projectRoot) {
  const root = fs.realpathSync(projectRoot);
  const projectId = digest(process.platform === 'win32' ? root.toLowerCase() : root);
  const directory = path.join(root, '.memory');
  const filename = path.join(directory, 'records.json');
  function inside(p) {
    const rel = path.relative(root, p);
    if (rel.startsWith('..') || path.isAbsolute(rel)) throw Error('Path outside project');
    return p;
  }
  function source(relative) {
    if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes('..')) throw Error('Invalid source path');
    const full = inside(fs.realpathSync(path.resolve(root, relative)));
    if (!fs.statSync(full).isFile()) throw Error('Source is not a file');
    if (relative.split(/[\\/]/).some(x => x === '.env' || x === '.git' || x === '.memory')) throw Error('Private source rejected');
    return {path: path.relative(root, full).replaceAll('\\', '/'), sha256: digest(fs.readFileSync(full))};
  }
  function prepare() {
    fs.mkdirSync(directory, {recursive: true}); inside(fs.realpathSync(directory));
    if (fs.existsSync(filename)) inside(fs.realpathSync(filename));
  }
  function load() {
    prepare();
    if (!fs.existsSync(filename)) return {schema: 1, project_id: projectId, records: {}, history: []};
    const db = JSON.parse(fs.readFileSync(filename, 'utf8'));
    if (db.project_id !== projectId || db.schema !== 1) throw Error('Project identity/schema mismatch');
    return db;
  }
  function mutate(action, id, fn) {
    if (!validId(id)) throw Error('Invalid record ID');
    prepare();
    const lock = path.join(directory, 'write.lock');
    const fd = fs.openSync(lock, 'wx');
    let temp;
    try {
      const db = load(); const before = db.records[id] || null; const result = fn(db);
      db.history.push({action, id, at: new Date().toISOString(), before, after: db.records[id] || null});
      temp = filename + '.' + crypto.randomUUID() + '.tmp';
      fs.writeFileSync(temp, JSON.stringify(db, null, 2), {flag: 'wx'});
      fs.renameSync(temp, filename);
      return {project_id: projectId, saved_path: filename, ...result};
    } finally {
      if (temp && fs.existsSync(temp)) fs.unlinkSync(temp);
      fs.closeSync(fd); fs.unlinkSync(lock);
    }
  }
  function body(params, revision) {
    if (!params.title?.trim() || !params.content?.trim() || !params.sources?.length) throw Error('Title, content and sources required');
    const sources = params.sources.map(source);
    let verification = null;
    if (params.sources.includes('artifacts/session-tests.json')) {
      const proof = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/session-tests.json'), 'utf8'));
      const fresh = Object.entries(proof.source_hashes).every(([p, h]) => source(p).sha256 === h);
      if (!fresh) throw Error('Test receipt is stale; rerun tests');
      verification = {exit_code: proof.exit_code, command: proof.command, tested_at: proof.tested_at};
    }
    return {id: params.id, project_id: projectId, title: params.title, content: params.content,
      sources, verification, revision, checked_at: new Date().toISOString()};
  }
  return {
    source,
    write(params) { return mutate('write', params.id, db => {
      if (db.records[params.id]) throw Error('Record already exists; update by ID');
      const record = body(params, 1); db.records[params.id] = record; return {record};
    }); },
    update(params) { return mutate('update', params.id, db => {
      const old = db.records[params.id]; if (!old) throw Error('Record not found');
      if (old.revision !== params.expected_revision) throw Error('Revision conflict');
      const record = body(params, old.revision + 1); db.records[params.id] = record; return {record};
    }); },
    read(id) {
      if (!validId(id)) throw Error('Invalid record ID');
      const record = load().records[id]; if (!record) throw Error('Record not found');
      const source_checks = record.sources.map(s => {
        try { return {...s, exists: true, unchanged: source(s.path).sha256 === s.sha256}; }
        catch { return {...s, exists: false, unchanged: false}; }
      });
      return {project_id: projectId, saved_path: filename, record, source_checks};
    },
    search(query = '') {
      const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
      const records = Object.values(load().records).filter(r => terms.every(t => `${r.id} ${r.title} ${r.content}`.toLowerCase().includes(t)));
      return {project_id: projectId, saved_path: filename, records};
    },
    delete(id, expected_revision) { return mutate('delete', id, db => {
      if (!db.records[id]) throw Error('Record not found');
      if (db.records[id].revision !== expected_revision) throw Error('Revision conflict');
      delete db.records[id]; return {deleted: id, scope: 'active records; history retained'};
    }); },
  };
}
