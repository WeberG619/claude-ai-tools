// Create a product and payment link on Stripe
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
  const tab = pages.find(p => p.url.includes('stripe.com'));
  if (!tab) { console.log('No Stripe tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(1000);

  // Check current page
  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  let text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 800));

  // Navigate to Payment Links creation
  console.log('\nNavigating to Payment Links...');
  await c.ev(`window.location.href = 'https://dashboard.stripe.com/payment-links/create'`);
  await sleep(5000);

  url = await c.ev('window.location.href');
  console.log('URL:', url);

  text = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('Page:', text.substring(0, 1500));

  // Look for form fields
  const inputs = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, select, textarea');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        var el = inputs[i];
        result.push({
          tag: el.tagName,
          type: el.type,
          name: el.name,
          id: el.id,
          placeholder: el.placeholder,
          value: el.value.substring(0, 50),
          label: el.getAttribute('aria-label') || '',
          visible: !!el.offsetParent
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nForm fields:', inputs);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
