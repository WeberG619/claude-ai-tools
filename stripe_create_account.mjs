// Create Stripe account
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
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('stripe.com'));
  if (!tab) { console.log('No Stripe tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Check current form state
  const formState = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          type: inputs[i].type,
          name: inputs[i].name,
          id: inputs[i].id,
          placeholder: inputs[i].placeholder,
          value: inputs[i].value,
          label: inputs[i].getAttribute('aria-label') || ''
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Form inputs:', formState);

  // Fill in the email field
  const setEmail = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].type === 'email' || inputs[i].name.includes('email') || inputs[i].placeholder.toLowerCase().includes('email')) {
          var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeSetter.call(inputs[i], 'weber@bimopsstudio.com');
          inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set email: ' + inputs[i].value;
        }
      }
      return 'No email input found';
    })()
  `);
  console.log(setEmail);
  await sleep(500);

  // Fill in the full name field
  const setName = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        var name = inputs[i].name.toLowerCase();
        var placeholder = inputs[i].placeholder.toLowerCase();
        var label = (inputs[i].getAttribute('aria-label') || '').toLowerCase();
        if (name.includes('name') || placeholder.includes('name') || label.includes('name')) {
          var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeSetter.call(inputs[i], 'Weber Gouin');
          inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set name: ' + inputs[i].value;
        }
      }
      return 'No name input found';
    })()
  `);
  console.log(setName);
  await sleep(500);

  // Check if country is already set to United States
  const countryCheck = await c.ev(`
    (() => {
      var selects = document.querySelectorAll('select');
      for (var i = 0; i < selects.length; i++) {
        return 'Select value: ' + selects[i].value + ', text: ' + selects[i].options[selects[i].selectedIndex].text;
      }
      // Check for custom dropdown
      var btns = document.querySelectorAll('[role="combobox"], [role="listbox"], button');
      var results = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.includes('United States') || btns[i].textContent.includes('Country')) {
          results.push(btns[i].textContent.trim().substring(0, 40));
        }
      }
      return 'Custom dropdowns: ' + JSON.stringify(results);
    })()
  `);
  console.log('Country:', countryCheck);

  // Click "Create account" button
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t.includes('Create account')) {
          btns[i].click();
          return 'Clicked: ' + t;
        }
      }
      return 'Not found';
    })()
  `);
  console.log(clicked);
  await sleep(8000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 1000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
