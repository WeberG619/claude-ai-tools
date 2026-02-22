// Click the "Add as new product" dropdown option
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

  // First, focus the search input and trigger the dropdown
  await c.ev(`
    (() => {
      var input = document.querySelector('input[placeholder*="Find or add"]');
      if (input) {
        input.focus();
        input.click();
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'Focused input';
      }
      return 'No input found';
    })()
  `);
  await sleep(1000);

  // Find and examine dropdown options
  const dropdownItems = await c.ev(`
    (() => {
      // Look for role="option" or role="listbox" items
      var options = document.querySelectorAll('[role="option"], [role="listbox"] > *, [class*="option"], [class*="dropdown"] li, [class*="menu"] li');
      var result = [];
      for (var i = 0; i < options.length; i++) {
        result.push({
          tag: options[i].tagName,
          role: options[i].getAttribute('role'),
          text: options[i].textContent.trim().substring(0, 80),
          class: options[i].className.substring(0, 60),
          visible: !!options[i].offsetParent,
          rect: JSON.stringify(options[i].getBoundingClientRect())
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Dropdown items:', dropdownItems.substring(0, 2000));

  // Try clicking with Input dispatch on Enter key to select
  // Or find the specific "Add ... as new product" element
  const found = await c.ev(`
    (() => {
      // Walk all elements and find exact text node
      var all = document.querySelectorAll('span, div, li, a, button, p');
      var candidates = [];
      for (var i = 0; i < all.length; i++) {
        var t = all[i].textContent.trim();
        if (t.includes('as new product') && !t.includes('Select type') && all[i].children.length < 3) {
          var rect = all[i].getBoundingClientRect();
          candidates.push({
            tag: all[i].tagName,
            text: t.substring(0, 80),
            class: all[i].className.substring(0, 60),
            w: rect.width,
            h: rect.height,
            top: rect.top,
            idx: i
          });
        }
      }
      return JSON.stringify(candidates, null, 2);
    })()
  `);
  console.log('\nCandidates:', found);

  // Click the most specific match using mouse events
  const clicked = await c.ev(`
    (() => {
      var all = document.querySelectorAll('span, div, li, a, button, p');
      for (var i = 0; i < all.length; i++) {
        var t = all[i].textContent.trim();
        if (t.includes('as new product') && all[i].children.length < 3) {
          var rect = all[i].getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            var x = rect.left + rect.width / 2;
            var y = rect.top + rect.height / 2;
            var events = ['mousedown', 'mouseup', 'click'];
            for (var j = 0; j < events.length; j++) {
              var ev = new MouseEvent(events[j], {
                bubbles: true, cancelable: true,
                clientX: x, clientY: y, view: window
              });
              all[i].dispatchEvent(ev);
            }
            return 'Mouse-clicked: ' + t.substring(0, 60) + ' at (' + Math.round(x) + ',' + Math.round(y) + ')';
          }
        }
      }
      return 'No visible match';
    })()
  `);
  console.log('\n' + clicked);
  await sleep(3000);

  // Check what happened
  let text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('\nAfter click:', text.substring(0, 1000));

  // Check for price input
  const priceFields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent) {
          var p = inputs[i].placeholder;
          var id = inputs[i].id;
          if (p.includes('0.00') || p.includes('price') || p.includes('amount') || id.includes('price') || id.includes('amount')) {
            result.push({ placeholder: p, id: id, type: inputs[i].type, value: inputs[i].value });
          }
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Price fields:', priceFields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
