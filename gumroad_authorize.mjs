// Click Continue on Google OAuth consent for Gumroad
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const googleTab = pages.find(p => p.url.includes('accounts.google.com'));
  if (!googleTab) { console.log('No Google tab'); process.exit(1); }

  const c = await connect(googleTab.webSocketDebuggerUrl);
  await sleep(500);

  // Click Continue / Allow button
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (t === 'continue' || t === 'allow' || t === 'sign in' || t === 'accept') {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      // List all buttons for debugging
      var all = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent) {
          all.push(btns[i].textContent.trim().substring(0, 30));
        }
      }
      return 'Buttons found: ' + JSON.stringify(all);
    })()
  `);
  console.log('Click result:', clicked);
  await sleep(10000);

  // Check tabs
  const allPages = await getPages();
  console.log('\nAll tabs:');
  for (const p of allPages) {
    console.log(' -', p.url.substring(0, 100));
  }

  // Check for Gumroad dashboard
  const gumTab = allPages.find(p => p.url.includes('gumroad.com'));
  if (gumTab) {
    const c2 = await connect(gumTab.webSocketDebuggerUrl);
    const url = await c2.ev('window.location.href');
    const text = await c2.ev(`document.body.innerText.substring(0, 1000)`);
    console.log('\nGumroad URL:', url);
    console.log('Gumroad:', text.substring(0, 500));
    c2.close();
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
