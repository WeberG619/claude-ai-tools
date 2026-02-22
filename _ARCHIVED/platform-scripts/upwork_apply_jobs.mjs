// Apply to top 2 Upwork jobs
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

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
    const nav = async (url) => { await send('Page.navigate', { url }); await sleep(5000); };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(10);
      }
    };
    const pressKey = async (key, code, vk) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: vk || 0 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(50);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, pressKey, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // ============ JOB 1: Revit 2025 add-in ============
  console.log('========== JOB 1: Revit 2025 Add-in ==========');
  await c.nav('https://www.upwork.com/jobs/Revit-2025-add_~022021630179255436296/');
  await sleep(3000);

  // Click "Apply now"
  const applyClicked1 = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button, a')].find(el =>
        el.textContent.trim().toLowerCase().includes('apply now') && el.offsetParent
      );
      if (btn) { btn.click(); return 'Clicked Apply Now'; }
      return 'Apply Now not found';
    })()
  `);
  console.log(applyClicked1);
  await sleep(5000);

  // Check what the application page looks like
  console.log('\n=== APPLICATION PAGE ===');
  const appPage1 = await c.ev(`
    (() => {
      const url = window.location.href;
      const main = document.querySelector('main') || document.body;
      const inputs = [...main.querySelectorAll('input, textarea, select')]
        .filter(el => el.offsetParent)
        .map(el => ({
          tag: el.tagName,
          type: el.type || '',
          name: el.name || '',
          placeholder: el.placeholder || '',
          id: el.id || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          label: el.closest('label')?.textContent?.trim()?.substring(0, 60) || ''
        }));
      const buttons = [...main.querySelectorAll('button')]
        .filter(b => b.offsetParent)
        .map(b => b.textContent.trim().substring(0, 40));
      const text = main.innerText.substring(0, 3000);
      return JSON.stringify({ url, inputs, buttons, text });
    })()
  `);
  console.log(appPage1);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
