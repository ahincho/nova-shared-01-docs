// Convierte los elementos que recibe el MCP de Excalidraw en un .excalidraw editable y su SVG,
// con la propia librería de Excalidraw corriendo en un Edge sin ventana. La página convierte el
// esqueleto con convertToExcalidrawElements, lo serializa y lo exporta; este script la maneja por
// el protocolo de depuración, espera a que termine y lee los dos resultados.
//
// Uso, desde diagrams/: node tools/export.mjs src/00-panorama.json 00-panorama
import { execFileSync, spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

const [, , input, outputBase] = process.argv;
const skeleton = JSON.parse(readFileSync(input, 'utf8'))
  .filter((e) => !['cameraUpdate', 'delete', 'restoreCheckpoint'].includes(e.type))
  .map(({ startBinding, endBinding, ...e }) => ({
    ...e,
    ...(startBinding ? { start: { id: startBinding.elementId } } : {}),
    ...(endBinding ? { end: { id: endBinding.elementId } } : {}),
  }));
const page = join(dirname(resolve(outputBase)), '.export.html');

writeFileSync(
  page,
  `<!doctype html><meta charset="utf-8"><body>
<script type="module">
const skeleton = ${JSON.stringify(skeleton)};
try {
  const lib = await import('https://esm.sh/@excalidraw/excalidraw@0.18.0?bundle-deps');
  const elements = lib.convertToExcalidrawElements(skeleton, { regenerateIds: false });
  const appState = { viewBackgroundColor: '#ffffff', exportBackground: true, exportWithDarkMode: false };
  const json = lib.serializeAsJSON(elements, appState, {}, 'local').replace('"source": "file://"', '"source": "https://excalidraw.com"');
  const svg = await lib.exportToSvg({ elements, appState, files: {}, exportPadding: 32 });
  window.__result = { json, svg: svg.outerHTML };
} catch (error) {
  window.__result = { error: String(error && error.stack || error) };
}
</script>`,
);

const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), 'nova-excalidraw-'));
const edge = spawn(
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'],
  { stdio: 'ignore' },
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function shutdown(code) {
  try {
    execFileSync('taskkill', ['/T', '/F', '/PID', String(edge.pid)], { stdio: 'ignore' });
  } catch {}
  try {
    rmSync(profile, { recursive: true, force: true });
  } catch {}
  process.exit(code);
}

try {
  let target;
  for (let i = 0; i < 40 && !target; i++) {
    await sleep(250);
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      target = list.find((t) => t.type === 'page');
    } catch {}
  }
  if (!target) throw new Error('Edge no abrió el puerto de depuración');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
  let id = 0;
  const pending = new Map();
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) pending.get(msg.id)(msg);
  };
  const send = (method, params = {}) =>
    new Promise((r) => {
      pending.set(++id, r);
      ws.send(JSON.stringify({ id, method, params }));
    });
  const evaluate = async (expression) =>
    (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value;

  await send('Page.navigate', { url: `file:///${page.replaceAll('\\', '/')}` });
  let result;
  for (let i = 0; i < 240 && !result; i++) {
    await sleep(250);
    result = await evaluate('window.__result');
  }
  if (!result) throw new Error('la exportación no terminó en 60 s');
  if (result.error) throw new Error(result.error);

  writeFileSync(`${outputBase}.excalidraw`, result.json.endsWith('\n') ? result.json : result.json + '\n');
  writeFileSync(`${outputBase}.svg`, result.svg + '\n');
  const texts = (result.svg.match(/<text/g) ?? []).length;
  const fonts = (result.svg.match(/@font-face/g) ?? []).length;
  console.log(
    `${outputBase}: ${JSON.parse(result.json).elements.length} elementos, ${texts} textos, ${fonts} fuentes, SVG de ${Math.round(result.svg.length / 1024)} KB`,
  );
  // La vista previa en PNG es para revisar el dibujo: se toma del SVG ya escrito, con su tamaño.
  const [, , w, h] = result.svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  await send('Emulation.setDeviceMetricsOverride', { width: Math.ceil(w), height: Math.ceil(h), deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: `file:///${resolve(`${outputBase}.svg`).replaceAll('\\', '/')}` });
  await sleep(1500);
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${outputBase}.preview.png`, Buffer.from(shot.result.data, 'base64'));
  rmSync(page, { force: true });
  shutdown(0);
} catch (error) {
  console.error(String(error.message ?? error).slice(0, 3000));
  shutdown(1);
}
