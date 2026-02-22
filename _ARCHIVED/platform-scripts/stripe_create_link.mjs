// Click Create link to generate payment link
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

  // Check if "Create link" is now enabled
  const createBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim() === 'Create link') {
          var rect = btns[i].getBoundingClientRect();
          return JSON.stringify({
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            disabled: btns[i].disabled,
            ariaDisabled: btns[i].getAttribute('aria-disabled')
          });
        }
      }
      return 'not found';
    })()
  `);
  console.log('Create link button:', createBtn);

  if (createBtn !== 'not found') {
    const btn = JSON.parse(createBtn);
    if (!btn.disabled) {
      console.log('Button is enabled! Clicking at (' + btn.x + ', ' + btn.y + ')');
      await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: btn.x, y: btn.y, button: 'left', clickCount: 1 });
      await sleep(50);
      await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: btn.x, y: btn.y, button: 'left', clickCount: 1 });
      await sleep(8000);

      const url = await c.ev('window.location.href');
      console.log('\nURL:', url);

      let text = await c.ev(`document.body.innerText.substring(0, 3000)`);
      console.log('Result:', text.substring(0, 1500));

      // Find payment link URL
      const link = await c.ev(`
        (() => {
          // Check inputs
          var inputs = document.querySelectorAll('input');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].value.includes('buy.stripe.com') || inputs[i].value.includes('stripe.com/pay')) {
              return inputs[i].value;
            }
          }
          // Check all visible text
          var text = document.body.innerText;
          var match = text.match(/https:\\/\\/buy\\.stripe\\.com\\/[a-zA-Z0-9_]+/);
          if (match) return match[0];
          // Check clipboard-related elements
          var clipEls = document.querySelectorAll('[class*="copy"], [class*="clip"], [class*="url"], [class*="link"]');
          for (var i = 0; i < clipEls.length; i++) {
            var t = clipEls[i].textContent;
            if (t.includes('buy.stripe.com')) return t.match(/https:\\/\\/buy\\.stripe\\.com\\/[a-zA-Z0-9_]+/)?.[0] || t;
          }
          return 'No link found';
        })()
      `);
      console.log('\nPayment link:', link);
    } else {
      console.log('Button is still disabled. Checking why...');
      let text = await c.ev(`document.body.innerText.substring(0, 1000)`);
      console.log(text.substring(0, 500));
    }
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
