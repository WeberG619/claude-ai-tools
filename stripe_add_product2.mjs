// Click the dropdown option to create the product, set price, and create link
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

  // Click the "Add 'Revit C# Add-in Starter Kit' as new product" dropdown option
  const addOption = await c.ev(`
    (() => {
      var all = document.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        var t = all[i].textContent.trim();
        if (t.includes("Add 'Revit") && t.includes('as new product')) {
          all[i].click();
          return 'Clicked: ' + t.substring(0, 60);
        }
      }
      // Also try role="option"
      var opts = document.querySelectorAll('[role="option"], [role="menuitem"], li');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.includes('new product')) {
          opts[i].click();
          return 'Clicked option: ' + opts[i].textContent.trim().substring(0, 60);
        }
      }
      return 'Not found';
    })()
  `);
  console.log(addOption);
  await sleep(2000);

  // Check what appeared - should show price input
  let text = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('After selecting:', text.substring(0, 1500));

  // Find all visible inputs now
  const fields = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input, select');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'hidden') {
          result.push({
            tag: inputs[i].tagName,
            type: inputs[i].type,
            placeholder: inputs[i].placeholder,
            id: inputs[i].id,
            name: inputs[i].name,
            value: inputs[i].value.substring(0, 30)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nVisible fields:', fields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
