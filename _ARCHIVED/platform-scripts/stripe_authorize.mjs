// Click Continue on Google OAuth consent for Stripe
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
      if (msg.method === 'Page.javascriptDialogOpening') {
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
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('accounts.google.com') || p.url.includes('stripe.com'));
  if (!tab) { console.log('No relevant tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Click "Continue" button
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Continue' || t === 'Allow') {
          btns[i].click();
          return 'Clicked: ' + t;
        }
      }
      // Also try spans/divs that look like buttons
      var all = document.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        if (all[i].textContent.trim() === 'Continue' && all[i].children.length === 0) {
          all[i].click();
          if (all[i].parentElement) all[i].parentElement.click();
          return 'Clicked Continue span/parent';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(clicked);
  await sleep(10000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 1000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
