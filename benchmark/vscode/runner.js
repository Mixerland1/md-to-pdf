const path = require('path');
const fs = require('fs');
const os = require('os');
const {spawnSync} = require('child_process');
const {downloadAndUnzipVSCode, resolveCliArgsFromVSCodeExecutablePath, runTests} = require('@vscode/test-electron');
(async () => {
  const version = '1.110.0';
  const executable = await downloadAndUnzipVSCode(version);
  const [cli, ...args] = resolveCliArgsFromVSCodeExecutablePath(executable);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'mdpdf-profile-'));
  const extensions = fs.mkdtempSync(path.join(os.tmpdir(), 'mdpdf-ext-'));
  const common = ['--extensions-dir', extensions, '--user-data-dir', profile, '--no-sandbox'];
  const install = spawnSync(cli, [...args, ...common, '--install-extension', 'yzane.markdown-pdf@2.2.0', '--force'], {stdio:'inherit'});
  if (install.status !== 0) throw Error('Extension install failed');
  await runTests({vscodeExecutablePath: executable, extensionDevelopmentPath: __dirname,
    extensionTestsPath: path.join(__dirname,'test.js'),
    launchArgs: [...common, '--disable-gpu','--disable-workspace-trust','--skip-welcome',path.resolve(process.argv[2])],
    extensionTestsEnv: {BENCHMARK_FOLDER:path.resolve(process.argv[2])}});
})().catch(e => { console.error(e); process.exit(1); });
