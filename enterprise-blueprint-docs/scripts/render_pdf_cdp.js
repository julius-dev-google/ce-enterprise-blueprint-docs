#!/usr/bin/env node
/**
 * Chrome DevTools Protocol (CDP) Headless PDF Renderer
 * ====================================================
 * Connects to headless Chrome via remote debugging WebSocket, loads the
 * pre-rendered HTML document, waits for client-side rendering (Mermaid diagrams,
 * KaTeX equations, syntax highlighting) to complete, and generates a print-ready
 * high-resolution PDF with background colors and vector graphics intact.
 *
 * Usage:
 *   node render_pdf_cdp.js <input_html_path> <output_pdf_path> [chrome_path]
 */

const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const inputArg = process.argv[2];
const outputArg = process.argv[3];
const chromeArg = process.argv[4];

if (!inputArg || !outputArg) {
  console.error('Usage: node render_pdf_cdp.js <input_html_path> <output_pdf_path> [chrome_path]');
  process.exit(1);
}

const inputHtml = path.resolve(inputArg.endsWith('.md') ? inputArg.replace(/\.md$/, '.html') : inputArg);
const outputPdf = path.resolve(outputArg);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findChromeBinary() {
  if (chromeArg && fs.existsSync(chromeArg)) {
    return chromeArg;
  }

  const envCandidates = [
    process.env.CHROME_BIN,
    process.env.GOOGLE_CHROME_BIN,
    process.env.CHROME_PATH,
    process.env.BROWSER
  ];
  for (const c of envCandidates) {
    if (c && fs.existsSync(c)) return c;
  }

  const standardPaths = [
    // macOS
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    // Linux
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/snap/bin/chromium',
    // Windows
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ];

  for (const p of standardPaths) {
    if (fs.existsSync(p)) return p;
  }

  return null;
}

async function renderPdfWithCDP() {
  if (!fs.existsSync(inputHtml)) {
    throw new Error(`Input HTML file not found: ${inputHtml}`);
  }

  const chromePath = findChromeBinary();
  if (!chromePath) {
    throw new Error('Google Chrome or Chromium executable could not be found.');
  }

  const outputDir = path.dirname(outputPdf);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const port = 9300 + Math.floor(Math.random() * 500);
  const profileDir = path.join(os.tmpdir(), `cdp_chrome_profile_${port}_${Date.now()}`);
  fs.mkdirSync(profileDir, { recursive: true });

  const cleanup = () => {
    try {
      if (fs.existsSync(profileDir)) {
        fs.rmSync(profileDir, { recursive: true, force: true });
      }
    } catch (_) {}
  };

  process.on('exit', cleanup);
  process.on('SIGINT', () => { cleanup(); process.exit(130); });
  process.on('SIGTERM', () => { cleanup(); process.exit(143); });

  const chromeProc = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-sandbox',
    '--disable-extensions',
    '--disable-software-rasterizer',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    'about:blank'
  ], { stdio: 'pipe' });

  chromeProc.on('error', (err) => {
    cleanup();
    throw new Error(`Failed to spawn Chrome process: ${err.message}`);
  });

  // Poll for Chrome debugger availability
  let wsUrl = null;
  for (let i = 0; i < 60; i++) {
    await sleep(200);
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) {
        const data = await res.json();
        wsUrl = data.webSocketDebuggerUrl;
        break;
      }
    } catch (_) {}
  }

  if (!wsUrl) {
    chromeProc.kill('SIGKILL');
    cleanup();
    throw new Error(`Failed to connect to Chrome DevTools on port ${port} within timeout.`);
  }

  // Connect via native WebSocket
  const ws = new WebSocket(wsUrl);
  let msgId = 1;
  const callbacks = new Map();

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.id && callbacks.has(msg.id)) {
        callbacks.get(msg.id)(msg);
        callbacks.delete(msg.id);
      }
    } catch (_) {}
  };

  const sendCommand = (method, params = {}) => {
    return new Promise((resolve, reject) => {
      const id = msgId++;
      callbacks.set(id, (res) => {
        if (res.error) reject(new Error(`${method} failed: ${res.error.message}`));
        else resolve(res.result);
      });
      ws.send(JSON.stringify({ id, method, params }));
    });
  };

  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  const { targetId } = await sendCommand('Target.createTarget', { url: `file://${inputHtml}` });
  const { sessionId } = await sendCommand('Target.attachToTarget', { targetId, flatten: true });

  const sendSessionCommand = (method, params = {}) => {
    return new Promise((resolve, reject) => {
      const id = msgId++;
      callbacks.set(id, (res) => {
        if (res.error) reject(new Error(`${method} failed: ${res.error.message}`));
        else resolve(res.result);
      });
      ws.send(JSON.stringify({ id, sessionId, method, params }));
    });
  };

  await sendSessionCommand('Page.enable');
  await sendSessionCommand('Runtime.enable');

  // Wait for client-side rendering (Mermaid diagrams, KaTeX, highlight.js)
  let renderComplete = false;
  for (let i = 0; i < 60; i++) {
    await sleep(250);
    try {
      const evalRes = await sendSessionCommand('Runtime.evaluate', {
        expression: 'window.__MERMAID_RENDER_COMPLETE__ === true'
      });
      if (evalRes && evalRes.result && evalRes.result.value === true) {
        renderComplete = true;
        break;
      }
    } catch (_) {}
  }

  if (!renderComplete) {
    console.warn('Warning: Timed out waiting for __MERMAID_RENDER_COMPLETE__; proceeding with print.');
  }

  // Small pause to allow styles and font metrics to settle
  await sleep(400);

  // Generate high-resolution PDF
  const pdfData = await sendSessionCommand('Page.printToPDF', {
    printBackground: true,
    paperWidth: 8.27,    // A4 width in inches
    paperHeight: 11.69,  // A4 height in inches
    marginTop: 0.39,     // ~10mm
    marginBottom: 0.39,  // ~10mm
    marginLeft: 0.47,    // ~12mm
    marginRight: 0.47,   // ~12mm
    preferCSSPageSize: true,
    displayHeaderFooter: false
  });

  const buffer = Buffer.from(pdfData.data, 'base64');
  fs.writeFileSync(outputPdf, buffer);

  ws.close();
  chromeProc.kill('SIGTERM');
  await sleep(150);
  cleanup();
}

renderPdfWithCDP().catch((err) => {
  console.error('CDP PDF Rendering failed:', err.message);
  process.exit(1);
});
