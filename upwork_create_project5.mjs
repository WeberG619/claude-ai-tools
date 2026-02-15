// Select suggested category and complete all steps
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
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, typeText, pressKey, selectAll, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Close any open modal first
  await c.ev(`
    (() => {
      var modal = document.querySelector('[role="dialog"]');
      if (modal) {
        var close = modal.querySelector('.air3-modal-close, button');
        if (close) close.click();
      }
    })()
  `);
  await sleep(1000);

  // Click the suggested category "Development & IT > Desktop Apps > Desktop App Improvements & Bug Fixes"
  // Actually, let's click "Design > Building Information Modeling > Other Building Information Modeling" - better fit
  console.log('=== SELECTING SUGGESTED CATEGORY ===');
  const catClicked = await c.ev(`
    (() => {
      var allEls = document.querySelectorAll('*');
      for (var i = 0; i < allEls.length; i++) {
        var el = allEls[i];
        if (el.offsetParent && el.textContent.trim().includes('Other Building Information Modeling') && el.children.length === 0) {
          var clickable = el.closest('button, a, [role="button"], [role="radio"], label, li') || el;
          clickable.click();
          return 'Clicked: ' + clickable.textContent.trim().substring(0, 80);
        }
      }
      // Try "Desktop App" as fallback
      for (var j = 0; j < allEls.length; j++) {
        var el2 = allEls[j];
        if (el2.offsetParent && el2.textContent.trim().includes('Desktop App Improvements') && el2.children.length === 0) {
          var clickable2 = el2.closest('button, a, [role="button"], [role="radio"], label, li') || el2;
          clickable2.click();
          return 'Clicked: ' + clickable2.textContent.trim().substring(0, 80);
        }
      }
      return 'Not found';
    })()
  `);
  console.log(catClicked);
  await sleep(2000);

  // Check if category was selected and project attributes appeared
  console.log('\n=== AFTER CATEGORY SELECT ===');
  const afterCat = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2500)`);
  console.log(afterCat);

  // Check for project attributes/delivery time etc
  console.log('\n=== FORM FIELDS ===');
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea, select');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        var el = inputs[i];
        if (el.offsetParent) {
          result.push({
            tag: el.tagName,
            type: el.type || '',
            id: el.id || '',
            placeholder: (el.placeholder || '').substring(0, 40),
            value: (el.value || '').substring(0, 40)
          });
        }
      }
      var dds = document.querySelectorAll('[role="combobox"]');
      var ddResult = [];
      for (var j = 0; j < dds.length; j++) {
        if (dds[j].offsetParent) {
          ddResult.push(dds[j].textContent.trim().substring(0, 60));
        }
      }
      return JSON.stringify({ inputs: result, dropdowns: ddResult });
    })()
  `);
  console.log(fields);

  // Fill in project attributes if any dropdowns appeared
  // Add tags
  console.log('\n=== ADDING TAGS ===');
  const tagInput = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].placeholder && inputs[i].placeholder.includes('typing')) {
          inputs[i].focus();
          return 'Focused';
        }
      }
      return 'Not found';
    })()
  `);
  console.log('Tag input:', tagInput);

  if (tagInput === 'Focused') {
    var tags = ['Revit API', 'C# Plugin', 'BIM Automation', 'Revit Add-in', 'Dynamo'];
    for (const tag of tags) {
      await c.typeText(tag);
      await sleep(800);
      await c.pressKey('Enter', 'Enter', 13);
      await sleep(500);
    }
  }

  // Click Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(3000);

  // Check Step 2 - Pricing
  console.log('\n========== STEP 2: PRICING ==========');
  const step2 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(step2);

  // Get pricing form fields
  const pricingFields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea, select');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        var el = inputs[i];
        if (el.offsetParent) {
          result.push({
            tag: el.tagName,
            type: el.type || '',
            id: el.id || '',
            placeholder: (el.placeholder || '').substring(0, 40),
            value: (el.value || '').substring(0, 40),
            name: el.name || ''
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nPricing fields:', pricingFields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
