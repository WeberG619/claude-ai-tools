// Add product and create payment link on Stripe
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
  await sleep(1000);

  // Click "Add new product"
  const addProduct = await c.ev(`
    (() => {
      var els = document.querySelectorAll('button, a, [role="button"], [role="option"]');
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim();
        if (t.includes('Add new product') || t === 'Add new product') {
          els[i].click();
          return 'Clicked: ' + t;
        }
      }
      // Try finding in dropdown
      var all = document.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        if (all[i].textContent.trim() === 'Add new product' && all[i].children.length === 0) {
          all[i].click();
          if (all[i].parentElement) all[i].parentElement.click();
          return 'Clicked Add new product span';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(addProduct);
  await sleep(2000);

  // Check what form appeared
  let text = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('After add product:', text.substring(0, 1000));

  // Look for product form fields
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"], input[type="number"], textarea');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          result.push({
            type: inputs[i].type || inputs[i].tagName,
            placeholder: inputs[i].placeholder,
            id: inputs[i].id,
            value: inputs[i].value.substring(0, 30),
            label: inputs[i].getAttribute('aria-label') || ''
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nVisible fields:', fields);

  // Fill in product name
  const setName = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        var p = inputs[i].placeholder.toLowerCase();
        if (p.includes('name') || p.includes('product')) {
          var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeSetter.call(inputs[i], 'Revit C# Add-in Starter Kit');
          inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('blur', { bubbles: true }));
          return 'Set name: ' + inputs[i].value;
        }
      }
      return 'No name input found';
    })()
  `);
  console.log(setName);
  await sleep(500);

  // Fill in price - look for price/amount input
  const setPrice = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        var p = inputs[i].placeholder.toLowerCase();
        var id = inputs[i].id.toLowerCase();
        if ((p.includes('price') || p.includes('amount') || p.includes('0.00') || id.includes('price') || id.includes('amount')) && inputs[i].offsetParent) {
          var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeSetter.call(inputs[i], '29.00');
          inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('blur', { bubbles: true }));
          return 'Set price: ' + inputs[i].value;
        }
      }
      return 'No price input found';
    })()
  `);
  console.log(setPrice);
  await sleep(500);

  // Make sure "One time" is selected (not recurring)
  const pricing = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="radio"], [role="tab"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'One time' || t === 'One-time') {
          btns[i].click();
          return 'Clicked: ' + t;
        }
      }
      return 'One-time not found (may already be selected)';
    })()
  `);
  console.log(pricing);
  await sleep(500);

  // Check form state
  const formCheck = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"], input[type="number"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          result.push({ placeholder: inputs[i].placeholder, value: inputs[i].value.substring(0, 30) });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Form values:', formCheck);

  // Click "Add product" button to confirm
  const confirm = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Add product' && btns[i].offsetParent) {
          btns[i].click();
          return 'Clicked: Add product';
        }
      }
      return 'Add product button not found';
    })()
  `);
  console.log(confirm);
  await sleep(3000);

  // Now click "Create link"
  const createLink = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Create link' || t === 'Create payment link') {
          btns[i].click();
          return 'Clicked: ' + t;
        }
      }
      return 'Create link not found';
    })()
  `);
  console.log(createLink);
  await sleep(5000);

  // Check result
  const url = await c.ev('window.location.href');
  console.log('\nURL:', url);

  text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Result:', text.substring(0, 1000));

  // Look for the payment link URL
  const linkUrl = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].value.includes('buy.stripe.com') || inputs[i].value.includes('checkout.stripe.com')) {
          return inputs[i].value;
        }
      }
      // Check for link in text
      var text = document.body.innerText;
      var match = text.match(/buy\\.stripe\\.com\\/[a-zA-Z0-9]+/);
      if (match) return 'https://' + match[0];
      match = text.match(/checkout\\.stripe\\.com\\/[a-zA-Z0-9\\/]+/);
      if (match) return 'https://' + match[0];
      return 'No payment link found';
    })()
  `);
  console.log('Payment link:', linkUrl);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
