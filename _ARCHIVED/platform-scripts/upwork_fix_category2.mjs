// Fix Upwork category - explore profile settings
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
        await sleep(20);
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

  // Navigate to profile settings
  console.log('=== PROFILE SETTINGS ===');
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(3000);

  const pageText = await c.ev('document.body.innerText.substring(0, 5000)');
  console.log(pageText);

  // Look for category-related elements
  console.log('\n=== CATEGORY ELEMENTS ===');
  const catElements = await c.ev(`
    (() => {
      const links = [...document.querySelectorAll('a')]
        .filter(a => a.offsetParent)
        .map(a => ({ text: a.textContent.trim().substring(0, 60), href: a.href }));
      const buttons = [...document.querySelectorAll('button')]
        .filter(b => b.offsetParent)
        .map(b => ({ text: b.textContent.trim().substring(0, 60), ariaLabel: b.getAttribute('aria-label') }));
      const selects = [...document.querySelectorAll('select')]
        .filter(s => s.offsetParent)
        .map(s => ({ name: s.name, id: s.id, value: s.value, options: [...s.options].map(o => o.text).slice(0, 5) }));
      return JSON.stringify({ links: links.slice(0, 20), buttons: buttons.slice(0, 20), selects });
    })()
  `);
  console.log(catElements);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
