// Submit fixed-price proposal - v2: don't mess with auto-filled amount
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
      if (msg.method === 'Page.javascriptDialogOpening') {
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
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
        await sleep(4);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Check current state — see if the amount is already there
  const currentAmount = await c.ev(`
    (() => {
      var el = document.getElementById('charged-amount-id');
      return el ? el.value : 'not found';
    })()
  `);
  console.log('Current amount:', currentAmount);

  // Fix the amount if corrupted — use React-compatible value setting
  if (currentAmount !== '$130.00') {
    console.log('Fixing amount...');
    await c.ev(`
      (() => {
        var el = document.getElementById('charged-amount-id');
        if (!el) return 'not found';
        // Use native setter to trigger React state update
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(el, '130');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'set to 130';
      })()
    `);
    await sleep(500);
  }

  // Verify amount
  const verifyAmount = await c.ev(`document.getElementById('charged-amount-id')?.value`);
  console.log('Amount now:', verifyAmount);

  // Check for duration — set it via React-compatible method
  const durationState = await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) {
          return combos[i].textContent.trim();
        }
      }
      return 'none';
    })()
  `);
  console.log('Duration current:', durationState);

  if (durationState.includes('Select')) {
    // Need to set duration
    await c.ev(`
      (() => {
        var combos = document.querySelectorAll('[role="combobox"]');
        for (var i = 0; i < combos.length; i++) {
          if (combos[i].offsetParent) {
            combos[i].click();
            return 'opened';
          }
        }
      })()
    `);
    await sleep(500);
    await c.ev(`
      (() => {
        var opts = document.querySelectorAll('[role="option"]');
        for (var i = 0; i < opts.length; i++) {
          if (opts[i].textContent.trim() === 'Less than 1 month') {
            opts[i].click();
            return 'selected';
          }
        }
      })()
    `);
    await sleep(500);
    console.log('Duration set');
  }

  // Check cover letter
  const hasCoverLetter = await c.ev(`
    (() => {
      var tas = document.querySelectorAll('textarea');
      for (var i = 0; i < tas.length; i++) {
        if (tas[i].offsetParent) return tas[i].value.length;
      }
      return 0;
    })()
  `);
  console.log('Cover letter chars:', hasCoverLetter);

  if (hasCoverLetter < 50) {
    console.log('Typing cover letter...');
    await c.ev(`
      (() => {
        var tas = document.querySelectorAll('textarea');
        for (var i = 0; i < tas.length; i++) {
          if (tas[i].offsetParent) { tas[i].focus(); return 'focused'; }
        }
      })()
    `);
    await c.selectAll();
    await sleep(100);
    await c.typeText(`Hi — I'm a Revit API specialist with deep experience in Autodesk's automation ecosystem. I build production C# add-ins and have worked extensively with the Revit API, Forge/APS Design Automation API, and Dynamo.

What I bring:
• Custom Revit API plugins (C#/.NET) — add-ins, ribbon tools, data extraction, batch processing
• Autodesk Platform Services (APS/Forge) and Design Automation API
• Named Pipes IPC for real-time Revit communication
• Multi-version support (Revit 2024, 2025, 2026)

I deliver complete Visual Studio solutions with source code, compiled DLLs, documentation, and installation guides. I can start immediately.

Happy to discuss your specific automation needs — what Revit workflows are you looking to automate?`);
    await sleep(500);
  }

  // Check ALL errors on the page
  const allErrors = await c.ev(`
    (() => {
      var all = document.querySelectorAll('.air3-form-message-error, .air3-alert-negative, [class*="error"]');
      var r = [];
      for (var i = 0; i < all.length; i++) {
        if (all[i].offsetParent && all[i].textContent.trim().length > 0 && all[i].textContent.trim().length < 100) {
          r.push(all[i].textContent.trim());
        }
      }
      return JSON.stringify(r);
    })()
  `);
  console.log('All errors:', allErrors);

  // Get full form state after all changes
  console.log('\n--- FORM STATE ---');
  const formText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(formText.substring(0, 2000));

  // Submit
  console.log('\n--- SUBMITTING ---');
  const submitResult = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && !btns[i].disabled && (t.includes('send for') || t.includes('submit'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'no submit';
    })()
  `);
  console.log(submitResult);
  await sleep(10000);

  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
  console.log('\nResult URL:', resultUrl);
  console.log('Result:', resultText.substring(0, 300));

  // If still on form, check errors
  if (resultUrl.includes('apply')) {
    const postErrors = await c.ev(`
      (() => {
        var all = document.querySelectorAll('.air3-form-message-error, .air3-alert-negative');
        var r = [];
        for (var i = 0; i < all.length; i++) {
          if (all[i].offsetParent) r.push(all[i].textContent.trim());
        }
        return JSON.stringify(r);
      })()
    `);
    console.log('Post-submit errors:', postErrors);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
