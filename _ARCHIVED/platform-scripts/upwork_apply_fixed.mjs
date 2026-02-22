// Apply to fixed-price Autodesk Automation API job
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
import { readFileSync } from 'fs';

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.method === 'Page.javascriptDialogOpening') {
        console.log('  [Auto-accepting dialog]');
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(4);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // We should be on or near the proposal page already, navigate to the job
  const jobs = JSON.parse(readFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', 'utf8'));
  const job = jobs[2]; // Autodesk Automation API

  console.log('Navigating to:', job.title);
  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
  await sleep(200);
  await c.ev(`window.location.href = ${JSON.stringify(job.href)}`);
  await sleep(5000);

  // Click Apply now
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, a');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t === 'apply now')) {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(6000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Get full form layout
  console.log('\n=== FORM LAYOUT ===');
  const formText = await c.ev(`(document.querySelector('main') || document.body).innerText`);
  console.log(formText.substring(0, 4000));

  // Get all inputs
  console.log('\n=== ALL INPUTS ===');
  const inputs = await c.ev(`
    (() => {
      var els = document.querySelectorAll('input, textarea, [role="combobox"], [role="spinbutton"]');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].offsetParent) {
          var section = els[i].closest('section, [class*="form"], [class*="milestone"]');
          result.push({
            tag: els[i].tagName,
            type: els[i].type || '',
            id: els[i].id || '',
            name: els[i].name || '',
            value: (els[i].value || '').substring(0, 50),
            placeholder: (els[i].placeholder || '').substring(0, 50),
            section: section ? section.textContent.trim().substring(0, 80) : '',
            role: els[i].getAttribute('role') || ''
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(inputs);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
