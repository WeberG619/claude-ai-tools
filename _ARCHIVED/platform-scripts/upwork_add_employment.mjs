// Add employment history via CDP
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
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(20);
      }
    };
    const pressTab = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
      await sleep(200);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, pressTab, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  const c = await connect(tab.webSocketDebuggerUrl);

  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(2000);

  // Click "Add employment"
  console.log('=== OPENING EMPLOYMENT DIALOG ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.getAttribute('aria-label') === 'Add employment history' ||
        b.textContent.trim() === 'Add employment'
      );
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    })()
  `);
  await sleep(2000);

  // Dump the modal to see field structure
  const modalContent = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const inputs = [...modal.querySelectorAll('input, textarea, select')].map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        placeholder: el.placeholder || '',
        id: el.id || '',
        label: el.closest('label')?.textContent?.trim()?.substring(0, 40) || '',
        ariaLabel: el.getAttribute('aria-label') || ''
      }));
      return JSON.stringify({ text: modal.innerText.substring(0, 1000), inputs });
    })()
  `);
  console.log('Modal:', modalContent);

  // Fill fields - Company
  console.log('\n=== FILLING FIELDS ===');
  const companySet = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const inputs = [...modal.querySelectorAll('input[type="text"], input:not([type])')];
      // First text input should be Company
      if (inputs[0]) {
        inputs[0].focus();
        return 'Focused company: ' + inputs[0].placeholder;
      }
      return 'no company input';
    })()
  `);
  console.log('Company: ' + companySet);
  await sleep(200);
  await c.selectAll();
  await c.typeText('BIM Ops Studio (Self-Employed)');
  await sleep(500);

  // Tab to City
  await c.pressTab();
  await sleep(300);
  await c.typeText('Sandpoint');
  await sleep(500);

  // Tab to Country - likely a dropdown, skip for now
  await c.pressTab();
  await sleep(300);

  // Tab to Title
  await c.pressTab();
  await sleep(300);

  // Check what field we're on
  const activeField = await c.ev(`document.activeElement?.tagName + '|' + document.activeElement?.placeholder + '|' + document.activeElement?.name`);
  console.log('Active field: ' + activeField);

  // Try to find and focus Title field directly
  const titleSet = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      // Look for the Title input - check labels
      const labels = [...modal.querySelectorAll('label')];
      const titleLabel = labels.find(l => l.textContent.trim() === 'Title');
      if (titleLabel) {
        const input = titleLabel.querySelector('input') || titleLabel.nextElementSibling?.querySelector('input') || modal.querySelector('input[name*="title"], input[id*="title"]');
        if (input) { input.focus(); return 'Focused title input'; }
      }
      // Try all text inputs - title is usually the 4th
      const inputs = [...modal.querySelectorAll('input[type="text"], input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])')];
      if (inputs.length >= 4) { inputs[3].focus(); return 'Focused 4th input: ' + inputs[3].placeholder; }
      return 'inputs count: ' + inputs.length;
    })()
  `);
  console.log('Title field: ' + titleSet);
  await sleep(200);
  await c.selectAll();
  await c.typeText('Principal / BIM Specialist');
  await sleep(500);

  // Set "I currently work here" checkbox
  const checkboxSet = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const checkbox = modal.querySelector('input[type="checkbox"]');
      if (checkbox && !checkbox.checked) {
        checkbox.click();
        return 'Checked: I currently work here';
      }
      return checkbox ? 'Already checked' : 'No checkbox found';
    })()
  `);
  console.log('Checkbox: ' + checkboxSet);
  await sleep(500);

  // Set From date - find the month/year selects
  const dateSet = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const selects = [...modal.querySelectorAll('select')];
      // Month select - set to January (value usually "1" or "01")
      if (selects.length >= 1) {
        const monthSelect = selects[0];
        monthSelect.value = '1';
        monthSelect.dispatchEvent(new Event('change', { bubbles: true }));
      }
      // Year select
      if (selects.length >= 2) {
        const yearSelect = selects[1];
        yearSelect.value = '2024';
        yearSelect.dispatchEvent(new Event('change', { bubbles: true }));
      }
      return 'Selects found: ' + selects.length + ' | values: ' + selects.map(s => s.value).join(', ');
    })()
  `);
  console.log('Date: ' + dateSet);
  await sleep(500);

  // Fill description
  const descSet = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const textarea = modal.querySelector('textarea');
      if (textarea) {
        textarea.focus();
        return 'Focused description textarea';
      }
      return 'No textarea';
    })()
  `);
  console.log('Description: ' + descSet);

  if (descSet.includes('Focused')) {
    await sleep(200);
    await c.selectAll();
    await c.typeText('Develop custom Revit API plugins (C#/.NET), automate BIM workflows, and produce construction document sets for commercial and residential architecture projects. Built RevitMCPBridge, an open-source tool connecting AI assistants to Revit for automated model operations.');
    await sleep(500);
  }

  // Dump final state before save
  console.log('\n=== MODAL STATE BEFORE SAVE ===');
  const finalModal = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      return modal.innerText.substring(0, 2000);
    })()
  `);
  console.log(finalModal);

  // Save
  const saved = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      const btn = [...modal.querySelectorAll('button')].find(b => b.textContent.trim().toLowerCase() === 'save');
      if (btn) { btn.click(); return 'Saved'; }
      return 'No save button';
    })()
  `);
  console.log('\nSave: ' + saved);
  await sleep(2000);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error(e.message); process.exit(1); });
