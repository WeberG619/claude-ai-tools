// Fill product form and create payment link
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

  // Step 1: Click "One-off" radio button
  const oneOff = await c.ev(`
    (() => {
      var radio = document.querySelector('input[value="oneOff"]');
      if (radio) {
        radio.click();
        return 'Clicked One-off radio';
      }
      // Try label
      var labels = document.querySelectorAll('label, span');
      for (var i = 0; i < labels.length; i++) {
        if (labels[i].textContent.trim() === 'One-off') {
          labels[i].click();
          return 'Clicked One-off label';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(oneOff);
  await sleep(500);

  // Step 2: Set price to 29.00
  const setPrice = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].placeholder === '0.00' && inputs[i].offsetParent) {
          inputs[i].focus();
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

  // Also type it natively via CDP
  // First click the price field
  const pricePos = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].placeholder === '0.00' && inputs[i].offsetParent) {
          var rect = inputs[i].getBoundingClientRect();
          return JSON.stringify({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });
        }
      }
      return null;
    })()
  `);

  if (pricePos) {
    const { x, y } = JSON.parse(pricePos);
    // Click the field
    await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 3 });
    await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 3 });
    await sleep(200);
    // Type the price
    await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 }); // Ctrl+A
    await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
    const chars = '29.00';
    for (const ch of chars) {
      await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: ch, text: ch });
      await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: ch });
    }
    console.log('Typed 29.00 via CDP');
  }
  await sleep(1000);

  // Step 3: Add a description
  const setDesc = await c.ev(`
    (() => {
      var textareas = document.querySelectorAll('textarea');
      for (var i = 0; i < textareas.length; i++) {
        if (textareas[i].offsetParent) {
          textareas[i].value = 'Production-ready Visual Studio solution for building Revit 2024-2026 add-ins. Multi-target C# codebase with sample commands, WPF dialogs, and 40+ helper methods.';
          textareas[i].dispatchEvent(new Event('input', { bubbles: true }));
          textareas[i].dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set description';
        }
      }
      return 'No textarea found';
    })()
  `);
  console.log(setDesc);
  await sleep(500);

  // Verify form state
  const formState = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"], textarea');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          result.push({ tag: inputs[i].tagName, placeholder: inputs[i].placeholder, value: inputs[i].value.substring(0, 50) });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Form state:', formState);

  // Step 4: Click "Add product"
  const addBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Add product' && btns[i].offsetParent) {
          btns[i].click();
          return 'Clicked: Add product';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(addBtn);
  await sleep(3000);

  // Check if product was added
  let text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('\nAfter adding product:', text.substring(0, 800));

  // Step 5: Click "Create link"
  const createLink = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Create link') {
          btns[i].click();
          return 'Clicked: Create link';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(createLink);
  await sleep(5000);

  // Get result
  const url = await c.ev('window.location.href');
  console.log('\nURL:', url);

  text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Result:', text.substring(0, 800));

  // Look for the payment link
  const paymentLink = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].value.includes('buy.stripe.com') || inputs[i].value.includes('stripe.com/pay')) {
          return inputs[i].value;
        }
      }
      // Check links in page
      var links = document.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        if (links[i].href.includes('buy.stripe.com')) {
          return links[i].href;
        }
      }
      // Check text
      var text = document.body.innerText;
      var match = text.match(/(https:\\/\\/buy\\.stripe\\.com\\/[a-zA-Z0-9_]+)/);
      if (match) return match[1];
      return 'No link found';
    })()
  `);
  console.log('Payment link:', paymentLink);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
