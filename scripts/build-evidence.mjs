import {build} from 'esbuild';
import {cp, mkdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = path.join(root, '.local', 'task02', 'site');
await mkdir(path.join(out, 'vendor'), {recursive: true});
await build({
  absWorkingDir: root, entryPoints: ['src/EvidenceViewer.tsx'],
  bundle: true, splitting: true, jsx: 'automatic', format: 'esm',
  target: 'es2022', outdir: path.join(out, 'assets'),
  entryNames: 'viewer', chunkNames: 'lib-[hash]',
});
const pdf = path.join(root, 'node_modules', 'pdfjs-dist');
await cp(path.join(root, 'public', 'favicon.svg'), path.join(out, 'assets', 'favicon.svg'));
await cp(path.join(pdf, 'build', 'pdf.worker.min.mjs'), path.join(out, 'vendor', 'pdf.worker.min.mjs'));
for (const dir of ['cmaps', 'standard_fonts', 'wasm']) {
  await cp(path.join(pdf, dir), path.join(out, 'vendor', dir), {recursive: true});
}
await writeFile(path.join(out, 'index.html'), `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>원문 검토 | 공시 검토실</title><link rel="icon" href="/assets/favicon.svg"><link rel="stylesheet" href="/assets/viewer.css"></head>
<body><div id="evidence-root"></div><script type="module" src="/assets/viewer.js"></script></body></html>`);
console.log('Built private evidence preview in .local/task02/site');
