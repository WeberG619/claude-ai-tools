// Find the correct Project Catalog URL
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

  // Go to profile page and find the "Manage projects" link
  console.log('=== FROM PROFILE PAGE ===');
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(3000);

  // Find the Manage projects link
  const manageLink = await c.ev(`
    (() => {
      const links = [...document.querySelectorAll('a')].filter(a =>
        a.textContent.trim().toLowerCase().includes('manage project') ||
        a.textContent.trim().toLowerCase().includes('create project') ||
        a.href?.includes('project') || a.href?.includes('catalog') || a.href?.includes('service')
      );
      return links.map(a => ({ text: a.textContent.trim(), href: a.href }));
    })()
  `);
  console.log('Project links:', JSON.stringify(manageLink));

  // Try "Deliver work" nav menu
  console.log('\n=== DELIVER WORK MENU ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button, a')].find(el =>
        el.textContent.trim().toLowerCase().includes('deliver work') && el.offsetParent
      );
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  const deliverMenu = await c.ev(`
    (() => {
      const items = [...document.querySelectorAll('a, button')]
        .filter(el => el.offsetParent)
        .filter(el => {
          const t = el.textContent.trim().toLowerCase();
          return t.includes('project') || t.includes('catalog') || t.includes('service') || t.includes('offering');
        })
        .map(el => ({ text: el.textContent.trim(), href: el.href || '', tag: el.tagName }));
      return JSON.stringify(items);
    })()
  `);
  console.log(deliverMenu);

  // Try various possible URLs
  const urls = [
    'https://www.upwork.com/nx/create-project/',
    'https://www.upwork.com/freelancers/create-service-profile',
    'https://www.upwork.com/services/manage',
    'https://www.upwork.com/nx/wm/projects/manage',
    'https://www.upwork.com/ab/create-project/',
  ];

  for (const tryUrl of urls) {
    console.log(`\nTrying: ${tryUrl}`);
    await c.nav(tryUrl);
    await sleep(3000);
    const resultUrl = await c.ev('window.location.href');
    const is404 = await c.ev(`document.body.innerText.includes("can't find")`);
    if (!is404) {
      console.log('FOUND! URL:', resultUrl);
      const text = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 2000)');
      console.log(text);
      break;
    } else {
      console.log('404');
    }
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
