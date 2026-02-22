// Click Google account for Stripe login - v2
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
  const tab = pages.find(p => p.url.includes('accounts.google.com') || p.url.includes('stripe.com'));
  if (!tab) { console.log('No relevant tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Examine the account chooser structure
  const structure = await c.ev(`
    (() => {
      // Google account chooser uses li[data-email] or div[data-identifier]
      var lis = document.querySelectorAll('li');
      var result = [];
      for (var i = 0; i < lis.length; i++) {
        var email = lis[i].getAttribute('data-email') || lis[i].getAttribute('data-identifier');
        result.push({
          tag: 'li',
          dataEmail: email,
          text: lis[i].textContent.trim().substring(0, 60),
          hasJsController: !!lis[i].getAttribute('jscontroller'),
          jsname: lis[i].getAttribute('jsname') || ''
        });
      }
      // Also check for div-based accounts
      var divs = document.querySelectorAll('div[data-email], div[data-identifier]');
      for (var i = 0; i < divs.length; i++) {
        result.push({
          tag: 'div',
          dataEmail: divs[i].getAttribute('data-email') || divs[i].getAttribute('data-identifier'),
          text: divs[i].textContent.trim().substring(0, 60)
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Account elements:', structure);

  // Try clicking using the data-email attribute or jscontroller
  const clicked = await c.ev(`
    (() => {
      // Method 1: li with data-email
      var el = document.querySelector('li[data-email*="bimops"]') || document.querySelector('li[data-email*="weber"]');
      if (el) { el.click(); return 'Clicked li[data-email]: ' + el.getAttribute('data-email'); }

      // Method 2: div with data-identifier
      el = document.querySelector('div[data-identifier*="bimops"]') || document.querySelector('div[data-identifier*="weber"]');
      if (el) { el.click(); return 'Clicked div[data-identifier]: ' + el.getAttribute('data-identifier'); }

      // Method 3: Find the account link/button that contains the email
      var all = document.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        if (all[i].getAttribute('data-email') && all[i].getAttribute('data-email').includes('bimops')) {
          all[i].click();
          return 'Clicked data-email element: ' + all[i].tagName + ' ' + all[i].getAttribute('data-email');
        }
      }

      // Method 4: Simulate click on the account row using dispatchEvent
      var lis = document.querySelectorAll('li');
      for (var i = 0; i < lis.length; i++) {
        if (lis[i].textContent.includes('bimopsstudio')) {
          var mousedown = new MouseEvent('mousedown', { bubbles: true, cancelable: true });
          var mouseup = new MouseEvent('mouseup', { bubbles: true, cancelable: true });
          var click = new MouseEvent('click', { bubbles: true, cancelable: true });
          lis[i].dispatchEvent(mousedown);
          lis[i].dispatchEvent(mouseup);
          lis[i].dispatchEvent(click);
          return 'Dispatched mouse events on li containing bimopsstudio';
        }
      }

      return 'No account element found';
    })()
  `);
  console.log(clicked);
  await sleep(8000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const text = await c.ev(`document.body.innerText.substring(0, 1000)`);
  console.log('Page:', text.substring(0, 500));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
