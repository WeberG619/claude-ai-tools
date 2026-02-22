// Check Stripe login status
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

  // List all open tabs
  console.log('Open tabs:');
  for (const p of pages) {
    console.log(' -', p.url.substring(0, 80));
  }

  // Use any tab to navigate to Stripe
  const tab = pages[0];
  if (!tab) { console.log('No tabs'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  console.log('\nNavigating to Stripe dashboard...');
  await c.ev(`window.location.href = 'https://dashboard.stripe.com/'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 1000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
