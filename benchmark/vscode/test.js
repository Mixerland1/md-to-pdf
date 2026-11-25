const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const {performance} = require('perf_hooks');
const sleep = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function run() {
  const folder = process.env.BENCHMARK_FOLDER;
  const ext = vscode.extensions.getExtension('yzane.markdown-pdf');
  if (!ext || ext.packageJSON.version !== '2.2.0') throw Error('Pinned extension unavailable');
  const cfg = vscode.workspace.getConfiguration('markdown-pdf');
  await cfg.update('format', 'A4', vscode.ConfigurationTarget.Workspace);
  if (fs.existsSync('/usr/bin/google-chrome')) {
    await cfg.update('executablePath','/usr/bin/google-chrome',vscode.ConfigurationTarget.Workspace);
    await cfg.update('chromium.autoDownload',false,vscode.ConfigurationTarget.Workspace);
  }
  await ext.activate();
  const timings = {};
  for (const name of fs.readdirSync(folder).filter(n=>n.endsWith('.md')).sort()) {
    const doc = await vscode.workspace.openTextDocument(path.join(folder,name));
    await vscode.window.showTextDocument(doc);
    const out = path.join(folder,name.replace(/\.md$/,'.pdf'));
    const values = [];
    for(let i=0;i<3;i++){
      if(fs.existsSync(out)) fs.unlinkSync(out);
      const start = performance.now();
      await vscode.commands.executeCommand('extension.markdown-pdf.pdf');
      let ready=false;
      for(let j=0;j<1200;j++){
        if(fs.existsSync(out)){
          const pdf=fs.readFileSync(out);
          if(pdf.subarray(-128).includes(Buffer.from('%%EOF'))){ ready=true; break; }
        }
        await sleep(100);
      }
      if(!ready) throw Error('Export did not produce a complete PDF: '+name);
      values.push(Math.round((performance.now()-start)*100)/100);
    }
    timings[path.basename(name,'.md')]=values;
  }
  fs.writeFileSync(path.join(folder,'timings.json'),JSON.stringify({version:ext.packageJSON.version,vscode:vscode.version,milliseconds:timings},null,2));
}
exports.run=run;
