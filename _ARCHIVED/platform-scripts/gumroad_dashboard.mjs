// Check Gumroad dashboard state and start creating a product
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
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }

  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Navigate to dashboard
  await c.ev(`window.location.href = 'https://app.gumroad.com/dashboard'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const pageText = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('Dashboard:', pageText.substring(0, 1500));

  // Check for existing products
  console.log('\n=== PRODUCTS ===');
  const products = await c.ev(`
    (() => {
      var body = document.body.innerText;
      if (body.includes('No products')) return 'no_products';
      if (body.includes('Create a product')) return 'has_create_button';
      return 'check_manually';
    })()
  `);
  console.log('Products state:', products);

  // Look for navigation / product links
  const navLinks = await c.ev(`
    (() => {
      var links = document.querySelectorAll('a');
      var result = [];
      for (var i = 0; i < links.length; i++) {
        if (links[i].offsetParent && links[i].href) {
          var t = links[i].textContent.trim();
          if (t.length > 0 && t.length < 40) {
            result.push({ text: t, href: links[i].href.substring(0, 80) });
          }
        }
      }
      return JSON.stringify(result.slice(0, 30), null, 1);
    })()
  `);
  console.log('\nNav links:', navLinks);

  // Navigate to products page
  console.log('\n=== PRODUCTS PAGE ===');
  await c.ev(`window.location.href = 'https://app.gumroad.com/products'`);
  await sleep(3000);
  const prodUrl = await c.ev('window.location.href');
  console.log('Products URL:', prodUrl);
  const prodText = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Products page:', prodText.substring(0, 800));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
