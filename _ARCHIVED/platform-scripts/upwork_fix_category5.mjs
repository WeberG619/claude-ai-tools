// Find the actual category edit controls
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

  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(3000);

  // Get the HTML of the entire category section more carefully
  console.log('=== CATEGORY SECTION DETAIL ===');
  const catSection = await c.ev(`
    (() => {
      // Find the "Categories" heading
      const allEls = [...document.querySelectorAll('*')];
      const catHeading = allEls.find(el =>
        el.textContent.trim() === 'Categories' && el.children.length === 0 && el.offsetParent
      );
      if (!catHeading) return 'No Categories heading found';

      // Go up to find the section container
      let section = catHeading;
      for (let i = 0; i < 4; i++) {
        if (section.parentElement) section = section.parentElement;
      }

      // Get all interactive elements in this section
      const buttons = [...section.querySelectorAll('a, button, [role="button"], [role="combobox"]')]
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 80),
          href: el.href || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          class: el.className.substring(0, 80),
          role: el.getAttribute('role') || ''
        }));

      // Get all dropdowns
      const dropdowns = [...section.querySelectorAll('[role="combobox"], select, [class*="dropdown"]')]
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 80),
          class: el.className.substring(0, 80),
          ariaLabel: el.getAttribute('aria-label') || '',
          ariaLabelledBy: el.getAttribute('aria-labelledby') || '',
          ariaExpanded: el.getAttribute('aria-expanded')
        }));

      return JSON.stringify({
        sectionHTML: section.innerHTML.substring(0, 3000),
        buttons,
        dropdowns
      });
    })()
  `);
  console.log(catSection);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
