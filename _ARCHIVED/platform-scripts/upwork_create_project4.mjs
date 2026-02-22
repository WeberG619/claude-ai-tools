// Continue from category modal - select dropdowns
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(10);
      }
    };
    const pressKey = async (key, code, vk) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: vk || 0 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, pressKey, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Check if modal is still open
  const modalOpen = await c.ev(`!!document.querySelector('[role="dialog"]')`);
  console.log('Modal open:', modalOpen);

  if (!modalOpen) {
    console.log('Modal closed, need to reopen...');
    c.close();
    process.exit(1);
  }

  // Click the "Select a category" dropdown
  console.log('=== OPENING CATEGORY DROPDOWN ===');
  await c.ev(`
    (() => {
      const dd = document.querySelector('[data-qa="categories-modal-l1-dropdown"] [role="combobox"]');
      if (dd) dd.click();
    })()
  `);
  await sleep(1500);

  // Get the dropdown options
  const opts = await c.ev(`
    (() => {
      var items = document.querySelectorAll('[role="option"]');
      var result = [];
      items.forEach(function(item) {
        if (item.offsetParent) {
          result.push(item.textContent.trim());
        }
      });
      return JSON.stringify(result);
    })()
  `);
  console.log('Category options:', opts);

  // Click "Engineering & Architecture"
  console.log('\n=== SELECTING ENGINEERING & ARCHITECTURE ===');
  const engClicked = await c.ev(`
    (() => {
      var items = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < items.length; i++) {
        if (items[i].offsetParent && items[i].textContent.trim().includes('Engineering')) {
          items[i].click();
          return 'Selected: ' + items[i].textContent.trim();
        }
      }
      return 'Engineering not found';
    })()
  `);
  console.log(engClicked);
  await sleep(2000);

  // Now the subcategory dropdown should be enabled
  console.log('\n=== OPENING SUBCATEGORY DROPDOWN ===');
  await c.ev(`
    (() => {
      var dd = document.querySelector('[data-qa="categories-modal-l3-dropdown"] [data-test="dropdown-toggle"]');
      if (dd) dd.click();
    })()
  `);
  await sleep(1500);

  const subOpts = await c.ev(`
    (() => {
      var items = document.querySelectorAll('[role="option"]');
      var result = [];
      items.forEach(function(item) {
        if (item.offsetParent) {
          result.push(item.textContent.trim());
        }
      });
      return JSON.stringify(result);
    })()
  `);
  console.log('Subcategory options:', subOpts);

  // Select "3D Modeling & CAD" or closest match
  const subSelected = await c.ev(`
    (() => {
      var items = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < items.length; i++) {
        if (items[i].offsetParent && items[i].textContent.trim().includes('3D Modeling')) {
          items[i].click();
          return 'Selected: ' + items[i].textContent.trim();
        }
      }
      // Try CAD
      for (var j = 0; j < items.length; j++) {
        if (items[j].offsetParent && items[j].textContent.trim().includes('CAD')) {
          items[j].click();
          return 'Selected: ' + items[j].textContent.trim();
        }
      }
      // Try Architecture
      for (var k = 0; k < items.length; k++) {
        if (items[k].offsetParent && items[k].textContent.trim().includes('Architect')) {
          items[k].click();
          return 'Selected: ' + items[k].textContent.trim();
        }
      }
      return 'No match found';
    })()
  `);
  console.log(subSelected);
  await sleep(1000);

  // Click Save
  console.log('\n=== SAVING CATEGORY ===');
  const saved = await c.ev(`
    (() => {
      var btn = document.querySelector('[data-qa="categories-modal-save-btn"]');
      if (btn && !btn.disabled) {
        btn.click();
        return 'Saved';
      }
      return btn ? 'Save disabled' : 'No save button';
    })()
  `);
  console.log(saved);
  await sleep(2000);

  // Check the overview form state
  console.log('\n=== OVERVIEW STATE ===');
  const overview = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(overview);

  // Add search tags
  console.log('\n=== ADDING TAGS ===');
  await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="search"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].placeholder && inputs[i].placeholder.includes('typing')) {
          inputs[i].focus();
          return 'Focused tag input';
        }
      }
      return 'Tag input not found';
    })()
  `);
  await sleep(300);

  const tags = ['Revit', 'C#', 'BIM', 'Revit API', 'Plugin Development'];
  for (const tag of tags) {
    await c.typeText(tag);
    await sleep(500);
    await c.pressKey('Enter', 'Enter', 13);
    await sleep(500);
  }

  // Check tags
  const tagCheck = await c.ev(`
    (() => {
      var tokens = document.querySelectorAll('[class*="token"], [class*="tag"], [class*="chip"]');
      var result = [];
      tokens.forEach(function(t) {
        if (t.offsetParent && t.textContent.trim().length < 40) {
          result.push(t.textContent.trim());
        }
      });
      return JSON.stringify(result);
    })()
  `);
  console.log('Tags:', tagCheck);

  // Click Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  const cont = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked Save & Continue';
        }
      }
      return 'Button not found';
    })()
  `);
  console.log(cont);
  await sleep(3000);

  // Check Step 2
  console.log('\n=== STEP 2: PRICING ===');
  const step2 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(step2);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
