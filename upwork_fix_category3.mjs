// Fix Upwork category - click Edit category and change to Engineering & Architecture
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

  // Make sure we're on the profile settings page
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(3000);

  // Click "Edit category"
  console.log('=== CLICKING EDIT CATEGORY ===');
  const editResult = await c.ev(`
    (() => {
      // Look for "Edit category" text - could be a link, button, or clickable element
      const allEls = [...document.querySelectorAll('*')];
      const editCat = allEls.find(el =>
        el.textContent.trim() === 'Edit category' && el.offsetParent
      );
      if (editCat) {
        editCat.click();
        return 'Clicked: ' + editCat.tagName + ' | ' + editCat.className;
      }
      // Try finding by partial text
      const partial = allEls.find(el =>
        el.textContent.trim().includes('Edit category') &&
        el.children.length === 0 &&
        el.offsetParent
      );
      if (partial) {
        partial.click();
        return 'Clicked partial: ' + partial.tagName;
      }
      return 'Edit category not found';
    })()
  `);
  console.log(editResult);
  await sleep(3000);

  // Check what appeared - modal or new page
  console.log('\\n=== AFTER CLICK ===');
  const afterClick = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (modal) return 'MODAL: ' + modal.innerText.substring(0, 2000);

      // Check if URL changed
      const url = window.location.href;

      // Check page content for category options
      const pageText = document.body.innerText.substring(0, 4000);
      return 'URL: ' + url + '\\n\\nPAGE: ' + pageText;
    })()
  `);
  console.log(afterClick);

  // Look for category selection elements
  console.log('\\n=== CATEGORY SELECTION UI ===');
  const catUI = await c.ev(`
    (() => {
      // Check for radio buttons, checkboxes, or links that might be category options
      const radios = [...document.querySelectorAll('input[type="radio"]')]
        .filter(r => r.offsetParent)
        .map(r => ({ name: r.name, value: r.value, checked: r.checked, label: r.closest('label')?.textContent?.trim()?.substring(0, 60) }));

      const checkboxes = [...document.querySelectorAll('input[type="checkbox"]')]
        .filter(c => c.offsetParent)
        .map(c => ({ name: c.name, value: c.value, checked: c.checked, label: c.closest('label')?.textContent?.trim()?.substring(0, 60) }));

      // Look for clickable category items
      const listItems = [...document.querySelectorAll('[role="option"], [role="radio"], [role="menuitem"], [role="tab"]')]
        .filter(el => el.offsetParent)
        .map(el => ({ text: el.textContent.trim().substring(0, 60), role: el.getAttribute('role'), selected: el.getAttribute('aria-selected') || el.getAttribute('aria-checked') }));

      // Any selects
      const selects = [...document.querySelectorAll('select')]
        .filter(s => s.offsetParent)
        .map(s => ({
          name: s.name,
          value: s.value,
          options: [...s.options].map(o => ({ text: o.text, value: o.value, selected: o.selected }))
        }));

      return JSON.stringify({ radios, checkboxes, listItems, selects });
    })()
  `);
  console.log(catUI);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
