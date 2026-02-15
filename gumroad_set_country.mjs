// Set country to United States on Gumroad and connect PayPal
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
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Select United States from the country dropdown
  console.log('Setting country to United States...');
  const countryResult = await c.ev(`
    (() => {
      var selects = document.querySelectorAll('select');
      for (var i = 0; i < selects.length; i++) {
        var opts = selects[i].options;
        for (var j = 0; j < opts.length; j++) {
          if (opts[j].text.includes('United States') && !opts[j].text.includes('Minor')) {
            selects[i].value = opts[j].value;
            selects[i].dispatchEvent(new Event('change', { bubbles: true }));
            return 'Selected: ' + opts[j].text + ' (value=' + opts[j].value + ')';
          }
        }
      }
      return 'not found';
    })()
  `);
  console.log(countryResult);
  await sleep(2000);

  // Check what appeared after selecting country
  const pageText = await c.ev(`document.body.innerText.substring(0, 3000)`);
  console.log('\nPage after country:', pageText.substring(0, 1500));

  // Look for Stripe connect or other payout options
  const payoutBtns = await c.ev(`
    (() => {
      var els = document.querySelectorAll('a, button');
      var r = [];
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim().toLowerCase();
        if (els[i].offsetParent && (t.includes('connect') || t.includes('stripe') || t.includes('paypal') || t.includes('bank') || t.includes('payout'))) {
          r.push({ text: els[i].textContent.trim().substring(0, 50), tag: els[i].tagName, href: (els[i].href || '').substring(0, 80) });
        }
      }
      return JSON.stringify(r, null, 2);
    })()
  `);
  console.log('\nPayout buttons:', payoutBtns);

  // Click Update settings to save
  console.log('\nSaving settings...');
  const saved = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Update settings')) {
          btns[i].click();
          return 'Clicked: Update settings';
        }
      }
      return 'not found';
    })()
  `);
  console.log(saved);
  await sleep(3000);

  const result = await c.ev(`document.body.innerText.substring(0, 500)`);
  console.log('Result:', result.substring(0, 300));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
