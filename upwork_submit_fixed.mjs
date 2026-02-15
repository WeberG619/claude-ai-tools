// Submit fixed-price proposal for Autodesk Automation API job
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
    const tab = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab' });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, tab, close: () => ws.close() });
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

  // We should already be on the proposal form
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  // Step 1: Select "By project" payment mode (simpler than milestones)
  console.log('\n--- Selecting "By project" payment ---');
  const radioResult = await c.ev(`
    (() => {
      var radios = document.querySelectorAll('input[name="milestoneMode"]');
      for (var i = 0; i < radios.length; i++) {
        if (radios[i].value === 'default') {
          radios[i].click();
          return 'Clicked: By project';
        }
      }
      return 'not found';
    })()
  `);
  console.log(radioResult);
  await sleep(1000);

  // Step 2: Check what the form looks like now
  const formAfter = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"], input[type="number"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          var label = '';
          var section = inputs[i].closest('section, [class*="form-group"], [class*="amount"]');
          if (section) label = section.textContent.trim().substring(0, 60);
          result.push({
            id: inputs[i].id || '',
            type: inputs[i].type,
            value: inputs[i].value || '',
            placeholder: inputs[i].placeholder || '',
            label: label
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Form inputs after selecting By project:', formAfter);

  // Step 3: Set the bid amount to $130
  console.log('\n--- Setting bid amount ---');
  const amountResult = await c.ev(`
    (() => {
      // Look for the amount/price input
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && (inputs[i].value === '$0.00' || inputs[i].id.includes('amount') || inputs[i].id.includes('price') || inputs[i].placeholder === '$0.00')) {
          inputs[i].focus();
          return 'Focused amount: ' + inputs[i].id + ' val=' + inputs[i].value;
        }
      }
      return 'not found';
    })()
  `);
  console.log(amountResult);

  if (amountResult.includes('Focused')) {
    await c.selectAll();
    await sleep(100);
    await c.typeText('130');
    console.log('Typed $130');
    await c.tab();
    await sleep(500);
  }

  // Step 4: Set project duration
  console.log('\n--- Setting duration ---');
  const durationCombo = await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) {
          combos[i].click();
          return 'Opened duration';
        }
      }
      return 'no combo';
    })()
  `);
  console.log(durationCombo);
  await sleep(500);

  const durationOpts = await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      var result = [];
      for (var i = 0; i < opts.length; i++) {
        result.push(opts[i].textContent.trim());
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Duration options:', durationOpts);

  // Select "Less than 1 month"
  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        var t = opts[i].textContent.trim().toLowerCase();
        if (t.includes('less than 1 month') || t.includes('less than a month') || t.includes('1 to 3 month')) {
          opts[i].click();
          return 'Selected: ' + opts[i].textContent.trim();
        }
      }
      // Take the first non-nav option
      for (var i = 0; i < opts.length; i++) {
        if (!opts[i].textContent.includes('Apply to') && !opts[i].textContent.includes('Find ')) {
          opts[i].click();
          return 'Selected: ' + opts[i].textContent.trim();
        }
      }
      return 'none';
    })()
  `);
  await sleep(500);

  // Step 5: Fill cover letter
  console.log('\n--- Typing cover letter ---');
  const focused = await c.ev(`
    (() => {
      var tas = document.querySelectorAll('textarea');
      for (var i = 0; i < tas.length; i++) {
        if (tas[i].offsetParent) { tas[i].focus(); return 'focused'; }
      }
      return 'none';
    })()
  `);
  if (focused === 'focused') {
    await c.selectAll();
    await sleep(100);
    const coverLetter = `Hi — I'm a Revit API specialist with deep experience in Autodesk's automation ecosystem. I build production C# add-ins and have worked extensively with the Revit API, Forge/APS Design Automation API, and Dynamo.

What I bring:
• Custom Revit API plugins (C#/.NET) — add-ins, ribbon tools, data extraction, batch processing
• Autodesk Platform Services (APS/Forge) and Design Automation API
• Named Pipes IPC for real-time Revit communication
• Multi-version support (Revit 2024, 2025, 2026)

I deliver complete Visual Studio solutions with source code, compiled DLLs, documentation, and installation guides. I can start immediately.

Happy to discuss your specific automation needs — what Revit workflows are you looking to automate?`;
    await c.typeText(coverLetter);
    console.log('Typed cover letter');
  }
  await sleep(500);

  // Step 6: Scroll down and submit
  await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(500);

  // Check for remaining errors
  const errors = await c.ev(`
    (() => {
      var errs = document.querySelectorAll('.air3-form-message-error');
      var r = [];
      for (var i = 0; i < errs.length; i++) {
        if (errs[i].offsetParent) r.push(errs[i].textContent.trim());
      }
      return JSON.stringify(r);
    })()
  `);
  console.log('Errors before submit:', errors);

  // Submit
  console.log('\n--- Submitting ---');
  const submitResult = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && !btns[i].disabled && (t.includes('send') || t.includes('submit'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'no submit';
    })()
  `);
  console.log(submitResult);
  await sleep(8000);

  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
  console.log('\nResult URL:', resultUrl);
  console.log('Result:', resultText.substring(0, 300));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
