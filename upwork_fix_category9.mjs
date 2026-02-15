// Select Engineering subcategories and save
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

  // Modal should still be open with Engineering & Architecture expanded
  const modalOpen = await c.ev(`!!document.querySelector('[role="dialog"]')`);
  console.log('Modal open:', modalOpen);

  if (!modalOpen) {
    console.log('Modal closed, reopening...');
    await c.nav('https://www.upwork.com/freelancers/settings/profile');
    await sleep(3000);
    await c.ev(`document.querySelector('button[aria-labelledby="editCategoryLabel"]')?.click()`);
    await sleep(3000);
    // Remove Content Writing
    await c.ev(`
      (() => {
        const modal = document.querySelector('[role="dialog"]');
        const removeBtn = [...modal.querySelectorAll('button')].find(el => el.textContent.trim().toLowerCase().includes('remove'));
        if (removeBtn) removeBtn.click();
      })()
    `);
    await sleep(1000);
    // Click Engineering & Architecture
    await c.ev(`
      (() => {
        const modal = document.querySelector('[role="dialog"]');
        const engBtn = [...modal.querySelectorAll('button')].find(el => el.textContent.trim() === 'Engineering & Architecture');
        if (engBtn) engBtn.click();
      })()
    `);
    await sleep(2000);
  }

  // Select "Building & Landscape Architecture"
  console.log('=== SELECTING SUBCATEGORIES ===');
  const selectArch = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const checkboxes = [...modal.querySelectorAll('input[type="checkbox"]')].filter(c => c.offsetParent);
      const archCb = checkboxes.find(c => c.closest('label')?.textContent?.trim() === 'Building & Landscape Architecture');
      if (archCb && !archCb.checked) {
        archCb.click();
        return 'Checked Building & Landscape Architecture';
      }
      return archCb ? 'Already checked' : 'Not found';
    })()
  `);
  console.log(selectArch);
  await sleep(500);

  // Select "3D Modeling & CAD"
  const selectCAD = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const checkboxes = [...modal.querySelectorAll('input[type="checkbox"]')].filter(c => c.offsetParent);
      const cadCb = checkboxes.find(c => c.closest('label')?.textContent?.trim() === '3D Modeling & CAD');
      if (cadCb && !cadCb.checked) {
        cadCb.click();
        return 'Checked 3D Modeling & CAD';
      }
      return cadCb ? 'Already checked' : 'Not found';
    })()
  `);
  console.log(selectCAD);
  await sleep(500);

  // Verify checkbox state before saving
  console.log('\\n=== CHECKBOX STATE ===');
  const checkState = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const checkboxes = [...modal.querySelectorAll('input[type="checkbox"]')]
        .filter(c => c.offsetParent)
        .map(c => ({
          label: c.closest('label')?.textContent?.trim(),
          checked: c.checked
        }));
      return JSON.stringify(checkboxes);
    })()
  `);
  console.log(checkState);

  // Check the overall modal text to see what's selected
  console.log('\\n=== MODAL TEXT ===');
  const modalText = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      return modal.innerText.substring(0, 2000);
    })()
  `);
  console.log(modalText);

  // Click Save
  console.log('\\n=== SAVING ===');
  const saved = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const saveBtn = [...modal.querySelectorAll('button')].find(b => b.textContent.trim().toLowerCase() === 'save');
      if (saveBtn) {
        if (saveBtn.disabled) return 'Save button is disabled';
        saveBtn.click();
        return 'Clicked Save';
      }
      return 'No save button';
    })()
  `);
  console.log(saved);
  await sleep(3000);

  // Verify the change
  console.log('\\n=== VERIFYING ===');
  const afterSave = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (modal) return 'Modal still open: ' + modal.innerText.substring(0, 500);

      // Check the category section on the settings page
      const label = document.getElementById('editCategoryLabel');
      if (label) {
        const section = label.parentElement?.parentElement;
        if (section) return 'Category section: ' + section.innerText;
      }
      return 'Page text: ' + document.body.innerText.substring(0, 2000);
    })()
  `);
  console.log(afterSave);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
