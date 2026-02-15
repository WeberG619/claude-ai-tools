// Use CDP Input.dispatchMouseEvent to click "Add as new product"
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

  // First ensure the dropdown is showing by focusing the input
  await c.ev(`
    (() => {
      var input = document.querySelector('input[placeholder*="Find or add"]');
      if (input) {
        input.focus();
        input.dispatchEvent(new Event('focus', { bubbles: true }));
        return 'focused';
      }
    })()
  `);
  await sleep(500);

  // Get the exact position of the dropdown [role="option"] element
  const pos = await c.ev(`
    (() => {
      var opt = document.querySelector('[role="option"]');
      if (opt) {
        var rect = opt.getBoundingClientRect();
        return JSON.stringify({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, text: opt.textContent.trim().substring(0, 60) });
      }
      return 'no option';
    })()
  `);
  console.log('Option position:', pos);

  if (pos !== 'no option') {
    const { x, y, text } = JSON.parse(pos);
    console.log('Clicking at (' + Math.round(x) + ', ' + Math.round(y) + '): ' + text);

    // Use CDP Input.dispatchMouseEvent for a real browser click
    await c.send('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x: Math.round(x),
      y: Math.round(y),
      button: 'left',
      clickCount: 1
    });
    await sleep(50);
    await c.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x: Math.round(x),
      y: Math.round(y),
      button: 'left',
      clickCount: 1
    });
    console.log('CDP mouse click dispatched');
    await sleep(3000);
  }

  // Check what happened
  let text = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('\nAfter click:', text.substring(0, 1500));

  // Check for new fields (price input)
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'hidden' && inputs[i].type !== 'checkbox') {
          result.push({
            type: inputs[i].type,
            placeholder: inputs[i].placeholder,
            id: inputs[i].id,
            value: inputs[i].value.substring(0, 30)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nFields:', fields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
