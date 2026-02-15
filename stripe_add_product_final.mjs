// Find and click the "Add product" button, then create link
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

  // Dump ALL buttons with their text and visibility
  const allBtns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        var rect = btns[i].getBoundingClientRect();
        result.push({
          idx: i,
          text: t.substring(0, 40),
          visible: rect.width > 0 && rect.height > 0,
          x: Math.round(rect.left + rect.width / 2),
          y: Math.round(rect.top + rect.height / 2),
          disabled: btns[i].disabled
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('All buttons:', allBtns);

  // Scroll the modal to bottom to find "Add product"
  const scrolled = await c.ev(`
    (() => {
      // Find the modal container and scroll it
      var modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"], [class*="Sheet"], [class*="drawer"]');
      var result = [];
      for (var i = 0; i < modals.length; i++) {
        if (modals[i].scrollHeight > modals[i].clientHeight) {
          modals[i].scrollTop = modals[i].scrollHeight;
          result.push('Scrolled modal: ' + modals[i].className.substring(0, 40) + ' scrollTop=' + modals[i].scrollTop);
        }
      }
      // Also scroll any overflow containers
      var scrollables = document.querySelectorAll('[style*="overflow"], [class*="scroll"]');
      for (var i = 0; i < scrollables.length; i++) {
        if (scrollables[i].scrollHeight > scrollables[i].clientHeight + 10) {
          scrollables[i].scrollTop = scrollables[i].scrollHeight;
          result.push('Scrolled: ' + scrollables[i].className.substring(0, 40));
        }
      }
      return result.length ? result.join(', ') : 'nothing scrolled';
    })()
  `);
  console.log('\n' + scrolled);
  await sleep(500);

  // Now find "Add product" button again
  const addBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Add product') {
          var rect = btns[i].getBoundingClientRect();
          btns[i].scrollIntoView({ behavior: 'instant', block: 'center' });
          rect = btns[i].getBoundingClientRect();
          return JSON.stringify({
            text: t,
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            visible: rect.width > 0 && rect.height > 0,
            disabled: btns[i].disabled
          });
        }
      }
      return 'not found';
    })()
  `);
  console.log('\nAdd product button:', addBtn);

  if (addBtn !== 'not found') {
    const { x, y } = JSON.parse(addBtn);
    console.log('Clicking Add product at (' + x + ', ' + y + ')');
    await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await sleep(50);
    await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    await sleep(3000);

    // Check result
    let text = await c.ev(`document.body.innerText.substring(0, 2000)`);
    console.log('\nAfter Add product:', text.substring(0, 800));

    // Now find and click "Create link"
    const createBtn = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim();
          if (t === 'Create link') {
            var rect = btns[i].getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2), disabled: btns[i].disabled });
          }
        }
        return 'not found';
      })()
    `);
    console.log('\nCreate link button:', createBtn);

    if (createBtn !== 'not found') {
      const pos = JSON.parse(createBtn);
      await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
      await sleep(50);
      await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
      console.log('Clicked Create link');
      await sleep(5000);

      const url = await c.ev('window.location.href');
      console.log('\nURL:', url);

      text = await c.ev(`document.body.innerText.substring(0, 2000)`);
      console.log('Result:', text.substring(0, 800));

      // Find payment link
      const link = await c.ev(`
        (() => {
          var all = document.querySelectorAll('input, a, [class*="link"]');
          for (var i = 0; i < all.length; i++) {
            var v = all[i].value || all[i].href || all[i].textContent;
            if (v && v.includes('buy.stripe.com')) return v;
          }
          var text = document.body.innerText;
          var m = text.match(/https:\\/\\/buy\\.stripe\\.com\\/[a-zA-Z0-9_]+/);
          return m ? m[0] : 'no link';
        })()
      `);
      console.log('Payment link:', link);
    }
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
