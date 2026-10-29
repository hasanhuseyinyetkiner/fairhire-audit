import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, resolve, join } from 'node:path';
import { mkdtemp, mkdir, copyFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
import net from 'node:net';

// Run with: node scripts/record-demo.mjs. Requires the project's installed frontend
// dependencies, .venv, Playwright Chromium/ffmpeg, and ffmpeg on PATH.
// Temporary files are deliberately retained; no project data or files are cleaned up.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const front = join(root, 'frontend');
const require = createRequire(join(front, 'package.json'));
const { chromium, expect } = require('@playwright/test');
const vite = await import(pathToFileURL(require.resolve('vite')).href);
const react = (await import(pathToFileURL(require.resolve('@vitejs/plugin-react')).href)).default;
const tailwind = (await import(pathToFileURL(require.resolve('@tailwindcss/vite')).href)).default;
const work = await mkdtemp(join(tmpdir(), 'fairhire-demo-'));
const backendPort = 18104, frontendPort = 15104;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontUrl = `http://127.0.0.1:${frontendPort}`;
const python = process.platform === 'win32' ? join(root, '.venv', 'Scripts', 'python.exe') : join(root, '.venv', 'bin', 'python');
const sqlite = join(work, 'synthetic.sqlite').replaceAll('\\', '/');
async function checkFree(port) {
  await new Promise((ok, fail) => {
    const s = net.createServer();
    s.once('error', () => fail(new Error(`Port ${port} is unavailable; refusing to reuse a server`)));
    s.listen(port, '127.0.0.1', () => s.close(ok));
  });
}
await checkFree(backendPort);
await checkFree(frontendPort);
const env = { ...process.env, FAIRHIRE_APP_ENV: 'demo', FAIRHIRE_SEED_DEMO: 'false',
  FAIRHIRE_BIND_HOST: '127.0.0.1', FAIRHIRE_ALLOW_NETWORK_BIND: 'false', FAIRHIRE_PORT: String(backendPort),
  FAIRHIRE_DATABASE_URL: `sqlite:///${sqlite}`, FAIRHIRE_UPLOAD_DIR: join(work, 'uploads'),
  FAIRHIRE_REPORT_DIR: join(work, 'reports'), FAIRHIRE_BOOTSTRAP_ITERATIONS: '200',
  FAIRHIRE_CORS_ORIGINS: frontUrl, PYTHONDONTWRITEBYTECODE: '1' };
console.log(`Temporary data and video: ${work}`);
// Only proceed after our own Uvicorn instance confirms it has bound the port.
const runner = `import asyncio, uvicorn\nfrom app.main import app\nfrom app.settings import enforce_bind, get_settings\nasync def run():\n s = get_settings()\n enforce_bind(s)\n server = uvicorn.Server(uvicorn.Config(app, host=s.bind_host, port=s.port))\n task = asyncio.create_task(server.serve())\n while not server.started and not task.done(): await asyncio.sleep(0.1)\n if server.started: print('OWN_API_BOUND', flush=True)\n await task\nasyncio.run(run())\n`;
const backend = spawn(python, ['-c', runner], { cwd: root, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
let backendOutput = '';
backend.stdout.on('data', data => { backendOutput += data; process.stdout.write(data); });
backend.stderr.on('data', data => { backendOutput += data; process.stderr.write(data); });
let server, browser, context;
try {
  const deadline = Date.now() + 90000;
  while (true) {
    if (backend.exitCode !== null || backend.signalCode) throw new Error('Backend exited before readiness');
    try { if (backendOutput.includes('OWN_API_BOUND') && (await fetch(`${backendUrl}/ready`)).ok) break; } catch {}
    if (Date.now() > deadline) throw new Error('Backend readiness timed out');
    await new Promise(r => setTimeout(r, 500));
  }
  server = await vite.createServer({ configFile: false, root: front, cacheDir: join(work, 'vite-cache'),
    plugins: [react(), tailwind()], server: { host: '127.0.0.1', port: frontendPort, strictPort: true,
      proxy: { '/api': backendUrl, '/health': backendUrl, '/ready': backendUrl } }, logLevel: 'warn' });
  await server.listen();
  browser = await chromium.launch({ headless: true });
  // Compile Vite modules before video recording so the clip begins with the app ready.
  const warm = await browser.newPage();
  await warm.goto(frontUrl, { waitUntil: 'networkidle' });
  await warm.close();
  context = await browser.newContext({ viewport: { width: 1000, height: 750 }, deviceScaleFactor: 1,
    recordVideo: { dir: work, size: { width: 1000, height: 750 } } });
  const page = await context.newPage();
  await page.goto(frontUrl, { waitUntil: 'networkidle' });
  await expect(page.getByTestId('demo-banner')).toContainText('synthetic');
  await page.waitForTimeout(1300);
  await page.getByTestId('generate-similar_accuracy_different_errors').click();
  await expect(page.getByRole('heading', { name: /Similar accuracy/ })).toBeVisible();
  await page.waitForTimeout(1300);
  await page.getByRole('button', { name: 'Run audit' }).click();
  await expect(page.getByTestId('confusion-matrix')).toBeVisible({ timeout: 60000 });
  await expect(page.getByTestId('cm-tn')).toContainText('91');
  await page.waitForTimeout(1800);
  await page.getByRole('link', { name: 'Group disparities' }).click();
  await expect(page.getByTestId('group-card-group_a')).toContainText('n = 100');
  await page.waitForTimeout(2000);
  await page.getByRole('link', { name: 'Audit report' }).click();
  await expect(page.getByRole('heading', { name: /record of the evidence/i })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download HTML' })).toBeVisible();
  await page.waitForTimeout(2000);
  const video = await page.video().path();
  await context.close(); context = undefined;
  const target = join(root, 'docs', 'assets', 'demo.gif');
  const converted = join(work, 'demo.gif');
  await mkdir(dirname(target), { recursive: true });
  // Palette is derived from the actual video, not from reconstructed still frames.
  const conversion = spawnSync('ffmpeg', ['-y', '-i', video, '-filter_complex',
    'fps=8,scale=1000:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
    '-loop', '0', converted], { stdio: 'inherit' });
  if (conversion.status !== 0) throw new Error('ffmpeg conversion failed');
  await copyFile(converted, target);
  console.log(`Recorded real UI workflow: ${target}`);
} finally {
  if (context) await context.close();
  if (browser) await browser.close();
  if (server) await server.close();
  if (backend.exitCode === null && backend.signalCode === null) {
    const exited = new Promise(resolve => backend.once('exit', resolve));
    if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(backend.pid), '/t', '/f'], { stdio: 'ignore', windowsHide: true });
    else backend.kill();
    await Promise.race([exited, new Promise(resolve => setTimeout(resolve, 5000))]);
  }
}
