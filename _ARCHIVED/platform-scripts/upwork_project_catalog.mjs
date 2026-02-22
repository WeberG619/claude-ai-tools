// Set up Project Catalog on Upwork
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Navigate to the project catalog / manage projects page
  console.log('=== NAVIGATING TO PROJECT CATALOG ===');

  // Try the manage projects URL
  await c.nav('https://www.upwork.com/services/product/manage');
  await sleep(3000);

  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  let pageText = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 3000)');
  console.log('Page:', pageText);

  // Look for "Create a project" or similar buttons
  console.log('\n=== INTERACTIVE ELEMENTS ===');
  const elements = await c.ev(`
    (() => {
      const btns = [...document.querySelectorAll('button, a')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
        .filter(el => {
          const t = el.textContent.trim().toLowerCase();
          return t.includes('create') || t.includes('project') || t.includes('add') || t.includes('new') || t.includes('catalog') || t.includes('service') || t.includes('manage');
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim(),
          href: el.href || '',
          class: el.className.substring(0, 60)
        }));
      return JSON.stringify(btns);
    })()
  `);
  console.log(elements);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
