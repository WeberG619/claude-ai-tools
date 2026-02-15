// Click the category edit button and change to Engineering & Architecture
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

  // Click the edit category button
  console.log('=== CLICKING EDIT CATEGORY BUTTON ===');
  const clicked = await c.ev(`
    (() => {
      const btn = document.querySelector('button[aria-labelledby="editCategoryLabel"]');
      if (btn) {
        btn.click();
        return 'Clicked edit category button';
      }
      return 'Button not found';
    })()
  `);
  console.log(clicked);
  await sleep(3000);

  // Check what appeared
  console.log('\\n=== AFTER CLICK - CHECK FOR MODAL/NEW UI ===');
  const afterClick = await c.ev(`
    (() => {
      // Check for modal
      const modal = document.querySelector('[role="dialog"]');
      if (modal) return 'MODAL: ' + modal.innerText.substring(0, 3000);

      // Check if URL changed
      const url = window.location.href;

      // Check for any new visible elements
      const pageText = document.body.innerText.substring(0, 5000);
      return 'URL: ' + url + '\\n' + pageText;
    })()
  `);
  console.log(afterClick);

  // Look for category selection UI elements
  console.log('\\n=== CATEGORY SELECTION UI ===');
  const selectionUI = await c.ev(`
    (() => {
      // Check for modal/dialog
      const modal = document.querySelector('[role="dialog"]');
      const container = modal || document.body;

      // Look for category-related interactive elements
      const radios = [...container.querySelectorAll('input[type="radio"]')]
        .filter(r => r.offsetParent)
        .map(r => ({
          name: r.name, value: r.value, checked: r.checked,
          label: r.closest('label')?.textContent?.trim()?.substring(0, 80) ||
                 document.querySelector('label[for="' + r.id + '"]')?.textContent?.trim()?.substring(0, 80)
        }));

      const checkboxes = [...container.querySelectorAll('input[type="checkbox"]')]
        .filter(c => c.offsetParent)
        .map(c => ({
          name: c.name, value: c.value, checked: c.checked,
          label: c.closest('label')?.textContent?.trim()?.substring(0, 80)
        }));

      const selects = [...container.querySelectorAll('select')]
        .filter(s => s.offsetParent)
        .map(s => ({
          name: s.name, value: s.value,
          options: [...s.options].map(o => ({ text: o.text.substring(0, 60), value: o.value, selected: o.selected }))
        }));

      const dropdowns = [...container.querySelectorAll('[role="combobox"], [class*="dropdown-toggle"]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          text: el.textContent.trim().substring(0, 80),
          ariaExpanded: el.getAttribute('aria-expanded'),
          ariaLabelledBy: el.getAttribute('aria-labelledby'),
          class: el.className.substring(0, 80)
        }));

      const listItems = [...container.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          selected: el.getAttribute('aria-selected'),
          role: el.getAttribute('role')
        }));

      return JSON.stringify({ radios, checkboxes, selects, dropdowns, listItems });
    })()
  `);
  console.log(selectionUI);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
