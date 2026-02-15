// Create the first Gumroad product - Revit C# Add-in Starter Kit
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
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Navigate to create new product
  console.log('Creating new product...');
  await c.ev(`window.location.href = 'https://gumroad.com/products/new'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Get form layout
  const formText = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('Form:', formText.substring(0, 1500));

  // Get all input fields
  const inputs = await c.ev(`
    (() => {
      var els = document.querySelectorAll('input, textarea, select, [contenteditable]');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].offsetParent) {
          var label = '';
          var labelEl = els[i].closest('label') || document.querySelector('label[for="' + els[i].id + '"]');
          if (labelEl) label = labelEl.textContent.trim().substring(0, 50);
          result.push({
            tag: els[i].tagName,
            type: els[i].type || '',
            id: els[i].id || '',
            name: els[i].name || '',
            placeholder: (els[i].placeholder || '').substring(0, 50),
            label: label,
            contentEditable: els[i].contentEditable || '',
            value: (els[i].value || '').substring(0, 30)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nInputs:', inputs);

  // Look for product name field
  console.log('\n--- Filling product name ---');
  const nameResult = await c.ev(`
    (() => {
      // Try finding by placeholder or label
      var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && (inputs[i].placeholder.toLowerCase().includes('name') || inputs[i].name.includes('name'))) {
          inputs[i].focus();
          return 'Found name: ' + inputs[i].placeholder;
        }
      }
      // Try first visible text input
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'hidden') {
          inputs[i].focus();
          return 'First input: ' + inputs[i].placeholder;
        }
      }
      return 'none';
    })()
  `);
  console.log(nameResult);

  if (nameResult !== 'none') {
    await c.selectAll();
    await sleep(100);
    await c.typeText('Revit C# Add-in Starter Kit');
    console.log('Typed product name');
    await sleep(500);
  }

  // Look for price field
  console.log('\n--- Setting price ---');
  const priceResult = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && (inputs[i].placeholder.includes('$') || inputs[i].name.includes('price') || inputs[i].id.includes('price') || inputs[i].type === 'number')) {
          inputs[i].focus();
          return 'Found price: placeholder=' + inputs[i].placeholder + ' type=' + inputs[i].type;
        }
      }
      return 'none';
    })()
  `);
  console.log(priceResult);

  if (priceResult !== 'none') {
    await c.selectAll();
    await sleep(100);
    await c.typeText('29');
    console.log('Typed price $29');
    await sleep(500);
  }

  // Check for any submit/create button
  console.log('\n--- Looking for Create button ---');
  const createBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, input[type="submit"]');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent) {
          result.push({
            text: btns[i].textContent.trim().substring(0, 40),
            type: btns[i].type || '',
            disabled: btns[i].disabled
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Buttons:', createBtn);

  // Take a snapshot of the current state
  console.log('\n--- Current form state ---');
  const currentForm = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log(currentForm.substring(0, 800));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
