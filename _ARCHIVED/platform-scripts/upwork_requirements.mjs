// Fill Requirements step and continue
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function addRequirement(c, questionText) {
  // Click "Add a requirement"
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Add a requirement')) {
          btns[i].click();
          return 'Clicked Add a requirement';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(clicked);
  await sleep(2000);

  // Check what appeared
  const formState = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea');
      var visible = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'search' && inputs[i].type !== 'hidden') {
          visible.push({
            tag: inputs[i].tagName,
            type: inputs[i].type || '',
            id: inputs[i].id || '',
            placeholder: (inputs[i].placeholder || '').substring(0, 60)
          });
        }
      }
      // Check for a modal or dialog
      var modal = document.querySelector('[role="dialog"]');
      var modalText = modal ? modal.innerText.substring(0, 500) : '';
      return JSON.stringify({ inputs: visible, modalText });
    })()
  `);
  console.log('Form state:', formState);

  const parsed = JSON.parse(formState);

  // Type the question into the visible input/textarea
  if (parsed.inputs.length > 0) {
    const target = parsed.inputs.find(i => i.tag === 'TEXTAREA') || parsed.inputs[0];
    await c.ev(`
      (() => {
        var el = document.querySelector('${target.tag === "TEXTAREA" ? "textarea" : "input"}[type="${target.type}"]');
        if (!el) {
          var inputs = document.querySelectorAll('${target.tag.toLowerCase()}');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent && inputs[i].type !== 'search' && inputs[i].type !== 'hidden') {
              el = inputs[i];
              break;
            }
          }
        }
        if (el) { el.focus(); el.value = ''; }
        return el ? 'Focused' : 'Not found';
      })()
    `);
    await sleep(200);
    await c.typeText(questionText);
    await sleep(500);
  }

  // Look for Save/Add/Done button in modal or form
  await sleep(500);
  const saved = await c.ev(`
    (() => {
      var modal = document.querySelector('[role="dialog"]');
      var scope = modal || document;
      var btns = scope.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t === 'save' || t === 'add' || t === 'done' || t === 'ok' || t.includes('add requirement'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'No save button found';
    })()
  `);
  console.log('Saved:', saved);
  await sleep(2000);
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  console.log('=== ADDING REQUIREMENTS ===');

  // Requirements for Revit plugin development
  const requirements = [
    'Which Revit version(s) do you need the plugin to support? (e.g., Revit 2024, 2025, 2026)',
    'Please describe the plugin functionality you need in detail. What workflow problem should it solve?',
    'Do you have any existing plugins, code, or Revit files I should build upon or reference?'
  ];

  for (const req of requirements) {
    console.log('\n--- Adding requirement ---');
    console.log('Question:', req.substring(0, 60) + '...');
    await addRequirement(c, req);
  }

  // Check current state
  console.log('\n=== REQUIREMENTS STATE ===');
  const state = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(state);

  // Click Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked Save & Continue';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(clicked);
  await sleep(5000);

  // Step 5: Description
  console.log('\n=== STEP 5: DESCRIPTION ===');
  const step5 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(step5);

  // Check form fields
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'search' && inputs[i].type !== 'hidden') {
          result.push({
            tag: inputs[i].tagName,
            type: inputs[i].type || inputs[i].getAttribute('contenteditable') || '',
            id: inputs[i].id || '',
            placeholder: (inputs[i].placeholder || inputs[i].getAttribute('data-placeholder') || '').substring(0, 80),
            value: (inputs[i].value || inputs[i].innerText || '').substring(0, 80)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nFields:', fields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
