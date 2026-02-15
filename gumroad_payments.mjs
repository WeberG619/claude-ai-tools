// Check Gumroad payment settings
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
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Navigate to payment settings
  console.log('Navigating to payment settings...');
  await c.ev(`window.location.href = 'https://gumroad.com/settings/payments'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('Page:', text.substring(0, 1500));

  // Look for connect buttons
  const connectBtns = await c.ev(`
    (() => {
      var els = document.querySelectorAll('a, button');
      var r = [];
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim().toLowerCase();
        if (els[i].offsetParent && (t.includes('connect') || t.includes('stripe') || t.includes('paypal') || t.includes('add') || t.includes('link'))) {
          r.push({ text: els[i].textContent.trim().substring(0, 40), tag: els[i].tagName, href: els[i].href || '' });
        }
      }
      return JSON.stringify(r, null, 2);
    })()
  `);
  console.log('\nConnect buttons:', connectBtns);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
