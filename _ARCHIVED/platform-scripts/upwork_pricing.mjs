// Fill pricing tiers and continue through remaining steps
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
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    const pressTab = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
      await sleep(200);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, selectAll, typeText, pressTab, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function fillField(c, fieldId, value) {
  await c.ev(`document.getElementById('${fieldId}')?.focus()`);
  await sleep(200);
  await c.selectAll();
  await sleep(100);
  await c.typeText(value);
  await sleep(300);
}

async function fillNumberField(c, fieldId, value) {
  await c.ev(`
    (() => {
      var el = document.getElementById('${fieldId}');
      if (el) {
        el.focus();
        el.select();
      }
    })()
  `);
  await sleep(200);
  await c.selectAll();
  await sleep(100);
  // Delete existing
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
  await sleep(100);
  await c.typeText(value);
  await sleep(300);
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  console.log('========== FILLING PRICING TIERS ==========');

  // Tier titles
  console.log('Setting tier titles...');
  await fillField(c, 'Starter-custom-tier-title', 'Simple Add-in');
  await fillField(c, 'Standard-custom-tier-title', 'Custom Plugin');
  await fillField(c, 'Advanced-custom-tier-title', 'Full Solution');

  // Tier descriptions
  console.log('Setting tier descriptions...');
  await fillField(c, 'Starter-custom-tier-description', 'Single-function Revit add-in with ribbon button and basic UI');
  await fillField(c, 'Standard-custom-tier-description', 'Multi-feature plugin with WPF dialog, error handling, and docs');
  await fillField(c, 'Advanced-custom-tier-description', 'Complex plugin suite with custom UI, API integration, and support');

  // Delivery days
  console.log('Setting delivery days...');
  await fillNumberField(c, 'Starter-days-to-fulfill', '5');
  await fillNumberField(c, 'Standard-days-to-fulfill', '14');
  await fillNumberField(c, 'Advanced-days-to-fulfill', '30');

  // Revisions - use the increment buttons or type directly
  console.log('Setting revisions...');
  // Find revision inputs and set them
  await c.ev(`
    (() => {
      // Revisions are number inputs that aren't the delivery day ones
      var inputs = document.querySelectorAll('input[type="number"]');
      var revisionInputs = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && !inputs[i].id.includes('days')) {
          revisionInputs.push(inputs[i]);
        }
      }
      // Starter: 1 revision, Standard: 2, Advanced: 3
      if (revisionInputs.length >= 3) {
        // Use native value setter to trigger React state
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(revisionInputs[0], '1');
        revisionInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        revisionInputs[0].dispatchEvent(new Event('change', { bubbles: true }));

        nativeInputValueSetter.call(revisionInputs[1], '2');
        revisionInputs[1].dispatchEvent(new Event('input', { bubbles: true }));
        revisionInputs[1].dispatchEvent(new Event('change', { bubbles: true }));

        nativeInputValueSetter.call(revisionInputs[2], '3');
        revisionInputs[2].dispatchEvent(new Event('input', { bubbles: true }));
        revisionInputs[2].dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set revisions: 1, 2, 3';
      }
      return 'Revision inputs found: ' + revisionInputs.length;
    })()
  `);
  await sleep(500);

  // Prices
  console.log('Setting prices...');
  await fillField(c, 'currency-input-0', '300');
  await c.pressTab();
  await sleep(500);
  await fillField(c, 'currency-input-1', '750');
  await c.pressTab();
  await sleep(500);
  await fillField(c, 'currency-input-2', '1500');
  await c.pressTab();
  await sleep(500);

  // Verify pricing state
  const pricingCheck = await c.ev(`
    (() => {
      return JSON.stringify({
        starterTitle: document.getElementById('Starter-custom-tier-title')?.value,
        standardTitle: document.getElementById('Standard-custom-tier-title')?.value,
        advancedTitle: document.getElementById('Advanced-custom-tier-title')?.value,
        starterDays: document.getElementById('Starter-days-to-fulfill')?.value,
        standardDays: document.getElementById('Standard-days-to-fulfill')?.value,
        advancedDays: document.getElementById('Advanced-days-to-fulfill')?.value,
        starterPrice: document.getElementById('currency-input-0')?.value,
        standardPrice: document.getElementById('currency-input-1')?.value,
        advancedPrice: document.getElementById('currency-input-2')?.value
      });
    })()
  `);
  console.log('\nPricing check:', pricingCheck);

  // Save & Continue to Step 3
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

  // Step 3 - Gallery
  console.log('\n========== STEP 3: GALLERY ==========');
  const step3 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(step3);

  // Skip gallery for now - just continue
  console.log('\nSkipping gallery...');
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

  // Step 4 - Requirements
  console.log('\n========== STEP 4: REQUIREMENTS ==========');
  const step4 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(step4);

  // Check form fields for requirements
  const reqFields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea, select');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          result.push({
            tag: inputs[i].tagName, type: inputs[i].type || '',
            id: inputs[i].id || '', placeholder: (inputs[i].placeholder || '').substring(0, 40)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nFields:', reqFields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
