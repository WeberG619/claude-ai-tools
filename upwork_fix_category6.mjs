// Zoom in on category section HTML
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

  // Find the editCategoryLabel and its parent section
  console.log('=== CATEGORY SECTION ===');
  const catHTML = await c.ev(`
    (() => {
      const label = document.getElementById('editCategoryLabel');
      if (!label) return 'No editCategoryLabel found';

      // Get the parent header and its next sibling (the content section)
      const header = label.parentElement; // <header>
      const section = header?.parentElement; // containing section

      return JSON.stringify({
        labelParent: header?.outerHTML?.substring(0, 500),
        sectionContent: section?.innerHTML?.substring(0, 3000),
        sectionTag: section?.tagName,
        sectionClass: section?.className
      });
    })()
  `);
  console.log(catHTML);

  // Also check: is there a pencil/edit icon button near the categories?
  console.log('\\n=== BUTTONS NEAR CATEGORIES ===');
  const nearButtons = await c.ev(`
    (() => {
      const label = document.getElementById('editCategoryLabel');
      if (!label) return 'no label';
      const header = label.parentElement;
      // Check all buttons/links in the header and nearby
      const section = header?.parentElement;
      if (!section) return 'no section';
      const btns = [...section.querySelectorAll('a, button, [role="button"]')]
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          ariaLabel: el.getAttribute('aria-label'),
          class: el.className.substring(0, 100),
          href: el.href || '',
          title: el.title || '',
          rect: el.getBoundingClientRect(),
          outerHTML: el.outerHTML.substring(0, 200)
        }));
      return JSON.stringify(btns);
    })()
  `);
  console.log(nearButtons);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
