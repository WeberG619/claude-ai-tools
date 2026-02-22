// Set cover image, upload PDF, and continue through remaining steps
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
        await sleep(8);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Step 1: Set cover image
  console.log('=== SETTING COVER IMAGE ===');
  const setCover = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && t.includes('set as project cover')) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      // Also check radio buttons or checkboxes
      var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
      for (var j = 0; j < inputs.length; j++) {
        var label = inputs[j].closest('label') || inputs[j].parentElement;
        if (label && label.textContent.trim().toLowerCase().includes('cover')) {
          inputs[j].click();
          return 'Clicked cover input: ' + label.textContent.trim();
        }
      }
      return 'No cover button found';
    })()
  `);
  console.log(setCover);
  await sleep(2000);

  // Step 2: Try uploading PDF (re-query DOM since it may have changed)
  console.log('\n=== UPLOADING PDF ===');
  const doc = await c.send('DOM.getDocument', { depth: -1 });
  const pdfInputs = await c.send('DOM.querySelectorAll', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"][accept=".pdf"]'
  });
  console.log('PDF inputs found:', pdfInputs.nodeIds?.length || 0);

  if (pdfInputs.nodeIds && pdfInputs.nodeIds.length > 0) {
    await c.send('DOM.setFileInputFiles', {
      files: ['D:\\_CLAUDE-TOOLS\\revit-plugin-services.pdf'],
      nodeId: pdfInputs.nodeIds[0]
    });
    console.log('PDF file set on input');

    // Dispatch events
    const evtResult = await c.ev(`
      (() => {
        var inputs = document.querySelectorAll('input[type="file"]');
        for (var i = 0; i < inputs.length; i++) {
          if (inputs[i].accept === '.pdf' && inputs[i].files.length > 0) {
            inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
            inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
            return 'Dispatched events. File: ' + inputs[i].files[0].name;
          }
        }
        return 'PDF input not found in JS';
      })()
    `);
    console.log(evtResult);
    await sleep(5000);
  }

  // Step 3: Click Continue
  console.log('\n=== CLICKING CONTINUE ===');
  const clickCont = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Continue') {
          btns[i].click();
          return 'Clicked Continue';
        }
      }
      return 'Continue not found';
    })()
  `);
  console.log(clickCont);
  await sleep(5000);

  // Step 4: Check what step we're on
  console.log('\n=== STEP 4: REQUIREMENTS ===');
  const step4Text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(step4Text);

  // Check form fields
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea, select');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          result.push({
            tag: inputs[i].tagName,
            type: inputs[i].type || '',
            id: inputs[i].id || '',
            placeholder: (inputs[i].placeholder || '').substring(0, 60),
            value: (inputs[i].value || '').substring(0, 60),
            name: inputs[i].name || ''
          });
        }
      }
      // Also check textareas within contenteditable divs
      var editables = document.querySelectorAll('[contenteditable="true"]');
      for (var j = 0; j < editables.length; j++) {
        if (editables[j].offsetParent) {
          result.push({
            tag: 'CONTENTEDITABLE',
            type: 'contenteditable',
            id: editables[j].id || '',
            placeholder: editables[j].getAttribute('data-placeholder') || '',
            value: editables[j].innerText.substring(0, 60),
            name: ''
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nForm fields:', fields);

  // Look for buttons/radio options on this step
  const buttons = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"], [role="radio"], [role="checkbox"]');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().length > 0 && btns[i].textContent.trim().length < 80) {
          result.push(btns[i].textContent.trim());
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nButtons:', buttons);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
