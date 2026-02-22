// Check Gumroad login state
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
  let tab = pages.find(p => p.url.includes('fiverr') || p.url.includes('upwork') || p.url.includes('gumroad'));
  if (!tab) tab = pages[0];
  if (!tab) { console.log('No tab found'); process.exit(1); }

  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}

  // Navigate to Gumroad
  console.log('Navigating to Gumroad...');
  await c.ev(`window.location.href = 'https://app.gumroad.com/dashboard'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const pageText = await c.ev(`document.body.innerText.substring(0, 1500)`);
  console.log('Page:', pageText.substring(0, 800));

  // Check login state
  if (url.includes('login') || url.includes('signup') || pageText.includes('Log in') || pageText.includes('Sign up')) {
    console.log('\nNot logged into Gumroad.');

    // Check if Google login is available
    const googleBtn = await c.ev(`
      (() => {
        var els = document.querySelectorAll('a, button');
        for (var i = 0; i < els.length; i++) {
          var t = els[i].textContent.trim().toLowerCase();
          if (t.includes('google') || t.includes('continue with')) {
            return els[i].textContent.trim();
          }
        }
        return 'none';
      })()
    `);
    console.log('Google login:', googleBtn);
  } else {
    console.log('\nLogged into Gumroad!');
    // Check for existing products
    const products = await c.ev(`
      (() => {
        var body = document.body.innerText;
        if (body.includes('Create a product') || body.includes('No products')) return 'no_products';
        return 'has_products';
      })()
    `);
    console.log('Products:', products);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
