// Interact with category modal dropdowns
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

  // Modal should be open - inspect interactive elements
  console.log('=== MODAL INTERACTIVE ELEMENTS ===');
  const modalElements = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      const comboboxes = [...modal.querySelectorAll('[role="combobox"]')]
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          ariaExpanded: el.getAttribute('aria-expanded'),
          class: el.className.substring(0, 80)
        }));

      const selects = [...modal.querySelectorAll('select')]
        .map(s => ({
          name: s.name, id: s.id, value: s.value,
          options: [...s.options].map(o => o.text).slice(0, 10)
        }));

      const clickable = [...modal.querySelectorAll('button, a, [tabindex], [role]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          role: el.getAttribute('role'),
          class: el.className.substring(0, 60)
        }));

      // Get the full HTML of the modal
      return JSON.stringify({ comboboxes, selects, clickable, html: modal.innerHTML.substring(0, 3000) });
    })()
  `);
  console.log(modalElements);

  // Click "Select a category" dropdown
  console.log('\n=== CLICKING SELECT A CATEGORY ===');
  const catDropdown = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      // Find dropdown toggle for "Select a category"
      const dd = [...modal.querySelectorAll('[role="combobox"], [class*="dropdown-toggle"], [data-test="dropdown-toggle"]')]
        .find(el => el.offsetParent);
      if (dd) {
        dd.click();
        return 'Clicked dropdown: ' + dd.textContent.trim().substring(0, 40) + ' | class: ' + dd.className.substring(0, 60);
      }

      // Try clicking text that says "Select a category"
      const selectText = [...modal.querySelectorAll('*')].find(el =>
        el.textContent.trim() === 'Select a category' && el.offsetParent
      );
      if (selectText) {
        selectText.click();
        return 'Clicked Select a category text';
      }

      return 'No dropdown found';
    })()
  `);
  console.log(catDropdown);
  await sleep(1500);

  // Check what options appeared
  const options = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      const opts = [...modal.querySelectorAll('[role="option"], [role="menuitem"], li, [class*="dropdown-item"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 60));

      // Also check for a listbox
      const listbox = modal.querySelector('[role="listbox"]');
      const listboxItems = listbox ? [...listbox.querySelectorAll('*')]
        .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim()) : [];

      return JSON.stringify({ options, listboxItems, pageText: modal.innerText.substring(0, 1500) });
    })()
  `);
  console.log('Options:', options);

  // Try to find and click Engineering & Architecture
  const engSelect = await c.ev(`
    (() => {
      const allEls = [...document.querySelectorAll('[role="option"], li, [class*="dropdown-item"]')]
        .filter(el => el.offsetParent);

      const eng = allEls.find(el => el.textContent.trim().includes('Engineering'));
      if (eng) {
        eng.click();
        return 'Selected: ' + eng.textContent.trim();
      }

      return 'Engineering not found in ' + allEls.length + ' options';
    })()
  `);
  console.log('Engineering select:', engSelect);
  await sleep(1500);

  // Check current state
  const afterEng = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      return modal.innerText.substring(0, 1500);
    })()
  `);
  console.log('\nAfter engineering:', afterEng);

  // Now click "Narrow down" dropdown for subcategory
  console.log('\n=== SUBCATEGORY ===');
  const subDropdown = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const dds = [...modal.querySelectorAll('[role="combobox"], [class*="dropdown-toggle"], [data-test="dropdown-toggle"]')]
        .filter(el => el.offsetParent);
      // Second dropdown for subcategory
      if (dds.length >= 2) {
        dds[1].click();
        return 'Clicked 2nd dropdown: ' + dds[1].textContent.trim().substring(0, 40);
      }
      // Or find the one that says "Narrow down"
      const narrow = dds.find(d => d.textContent.trim().includes('Narrow'));
      if (narrow) {
        narrow.click();
        return 'Clicked Narrow: ' + narrow.textContent.trim();
      }
      return 'Dropdowns found: ' + dds.map(d => d.textContent.trim().substring(0, 30)).join(' | ');
    })()
  `);
  console.log(subDropdown);
  await sleep(1500);

  const subOptions = await c.ev(`
    (() => {
      const opts = [...document.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent)
        .map(el => el.textContent.trim());
      return JSON.stringify(opts.slice(0, 15));
    })()
  `);
  console.log('Subcategory options:', subOptions);

  // Select 3D Modeling & CAD
  const subSelect = await c.ev(`
    (() => {
      const opts = [...document.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent);
      const target = opts.find(o => o.textContent.trim().includes('3D Modeling')) ||
                     opts.find(o => o.textContent.trim().includes('CAD')) ||
                     opts.find(o => o.textContent.trim().includes('Architecture'));
      if (target) { target.click(); return 'Selected: ' + target.textContent.trim(); }
      return 'Not found';
    })()
  `);
  console.log('Subcategory select:', subSelect);
  await sleep(1000);

  // Click Save on the modal
  console.log('\n=== SAVING CATEGORY ===');
  const saved = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const saveBtn = [...modal.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase() === 'save' && b.offsetParent
      );
      if (saveBtn && !saveBtn.disabled) { saveBtn.click(); return 'Saved'; }
      return saveBtn ? 'Save disabled' : 'No save button';
    })()
  `);
  console.log(saved);
  await sleep(2000);

  // Check overview state
  console.log('\n=== OVERVIEW STATE ===');
  const overview = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1500)`);
  console.log(overview);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
