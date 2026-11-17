/** Run credential-free DSH native refresh probes against an explicitly selected installation. */
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {copyFileSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';

const {values} = parseArgs({options: {
  'runtime-node-modules': {type: 'string'},
  report: {type: 'string'},
}});
if (!values['runtime-node-modules']) {
  throw new Error('Pass --runtime-node-modules for the selected native installation');
}
const modules = realpathSync(resolve(values['runtime-node-modules']));
const here = dirname(fileURLToPath(import.meta.url));
const installed = name => join(modules, '@deepseek-ai', name);
const packages = ['dsh', 'dsh-hmr', 'dsh-app-boot', 'dsh-skill', 'dsh-skill-filesystem', 'dsh-mcp-manager'];
const versionEvidence = Object.fromEntries(packages.map(name => {
  const path = join(installed(name), 'package.json');
  const bytes = readFileSync(path);
  return [name, {
    version: JSON.parse(bytes).version,
    entry_sha256: createHash('sha256').update(readFileSync(join(installed(name), 'lib', name === 'dsh' ? 'bin.js' : 'index.js'))).digest('hex'),
  }];
}));
const root = mkdtempSync(join(tmpdir(), 'houmao-dsh-refresh-qualification-'));
const privateHome = join(root, 'user-home');
const privateTmp = join(root, 'temporary');
for (const path of [privateHome, privateTmp, 'config', 'cache', 'data'].map((path, index) => index < 2 ? path : join(privateHome, path))) {
  mkdirSync(path, {recursive: true});
}
const nativeEnvironment = {
  PATH: process.env.PATH ?? '/usr/bin:/bin',
  HOME: privateHome,
  TMPDIR: privateTmp,
  XDG_CONFIG_HOME: join(privateHome, 'config'),
  XDG_CACHE_HOME: join(privateHome, 'cache'),
  XDG_DATA_HOME: join(privateHome, 'data'),
  LANG: 'C.UTF-8',
};
const execute = script => JSON.parse(execFileSync(process.execPath,
  ['--expose-internals', script, modules],
  {env: nativeEnvironment, cwd: root, encoding: 'utf8', timeout: 45000, stdio: ['ignore', 'pipe', 'pipe']},
));
try {
  const negative = join(root, 'hmr-negative');
  const host = join(negative, 'node_modules', 'host-package');
  mkdirSync(host, {recursive: true});
  writeFileSync(join(host, 'package.json'), JSON.stringify({
    name: 'host-package', version: '1.0.0', type: 'module', exports: './index.mjs',
  }));
  writeFileSync(join(host, 'index.mjs'), 'export const value=1;\n');
  const worker = join(negative, 'entry.mjs');
  copyFileSync(join(here, 'hmr-worker.mjs'), worker);
  const report = {
    schema_version: 1,
    runtime_node_modules: modules,
    node_version: process.version,
    versions: versionEvidence,
    sdk: execute(join(here, 'sdk-probe.mjs')),
    mcp: execute(join(here, 'mcp-probe.mjs')),
    hmr_negative: execute(worker),
    model_requests: 0,
    tmux_used: false,
    ambient_auth: false,
    status: 'passed',
    completed_at: new Date().toISOString(),
    limitations: [
      'The SDK probes create no Agent or model turn; run the separate controlled Web check for bound-session evidence.',
      'MCP removal demonstrates tool withdrawal, not independently verified child-process closure.',
      'HMR negative results intentionally demonstrate unsafe automatic activation and partial native effects.',
      'This utility does not establish a safe universal module-reload or preflight contract.',
    ],
  };
  const output = `${JSON.stringify(report, null, 2)}\n`;
  if (values.report) writeFileSync(resolve(values.report), output, {mode: 0o600});
  process.stdout.write(output);
} finally {
  rmSync(root, {recursive: true, force: true});
}
