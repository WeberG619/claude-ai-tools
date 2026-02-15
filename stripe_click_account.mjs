// Click Google account for Stripe login
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

  // Click on the weber@bimopsstudio.com account
  const clicked = await c.ev(`
    (() => {
      var els = document.querySelectorAll('li, div[data-email], [data-identifier], a');
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent;
        if (t.includes('weber@bimopsstudio.com') || t.includes('Weber Gouin')) {
          els[i].click();
          return 'Clicked: ' + t.trim().substring(0, 60);
        }
      }
      // Try broader search
      var allEls = document.querySelectorAll('*');
      for (var i = 0; i < allEls.length; i++) {
        if (allEls[i].textContent.includes('bimopsstudio') && allEls[i].children.length < 5) {
          allEls[i].click();
          return 'Clicked element with bimopsstudio: ' + allEls[i].tagName;
        }
      }
      return 'Not found';
    })()
  `);
  console.log(clicked);
  await sleep(8000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 1000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
