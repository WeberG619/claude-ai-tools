// Scroll to find Add product button and click it
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

  // Find all scrollable containers and their dimensions
  const scrollContainers = await c.ev(`
    (() => {
      var all = document.querySelectorAll('*');
      var result = [];
      for (var i = 0; i < all.length; i++) {
        var el = all[i];
        if (el.scrollHeight > el.clientHeight + 20 && el.clientHeight > 100) {
          var style = window.getComputedStyle(el);
          if (style.overflow === 'auto' || style.overflow === 'scroll' || style.overflowY === 'auto' || style.overflowY === 'scroll') {
            result.push({
              tag: el.tagName,
              class: el.className.substring(0, 50),
              scrollHeight: el.scrollHeight,
              clientHeight: el.clientHeight,
              scrollTop: el.scrollTop,
              idx: i
            });
          }
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Scroll containers:', scrollContainers);

  // Scroll ALL scrollable containers to the bottom
  const scrolled = await c.ev(`
    (() => {
      var all = document.querySelectorAll('*');
      var scrolled = [];
      for (var i = 0; i < all.length; i++) {
        var el = all[i];
        if (el.scrollHeight > el.clientHeight + 20 && el.clientHeight > 100) {
          var style = window.getComputedStyle(el);
          if (style.overflow === 'auto' || style.overflow === 'scroll' || style.overflowY === 'auto' || style.overflowY === 'scroll') {
            el.scrollTop = el.scrollHeight;
            scrolled.push(el.className.substring(0, 30) + ' -> scrollTop=' + el.scrollTop);
          }
        }
      }
      return scrolled.join(', ');
    })()
  `);
  console.log('Scrolled:', scrolled);
  await sleep(500);

  // Now look for ALL buttons again
  const btns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        var rect = btns[i].getBoundingClientRect();
        if (t.includes('Add') || t.includes('Cancel') || t.includes('Create') || t.includes('product')) {
          result.push({
            idx: i,
            text: t.substring(0, 40),
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            visible: rect.width > 0,
            disabled: btns[i].disabled
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nRelevant buttons after scroll:', btns);

  // Try using keyboard - press Tab to get to the button, or use DOM scroll
  const addProductBtn = await c.ev(`
    (() => {
      // Search by text content more broadly
      var btns = document.querySelectorAll('button, [role="button"], input[type="submit"]');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t === 'Add product' || t === 'Save product') {
          // Scroll it into view
          btns[i].scrollIntoView({ behavior: 'instant', block: 'center' });
          var rect = btns[i].getBoundingClientRect();
          return JSON.stringify({
            text: t,
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            w: rect.width,
            h: rect.height
          });
        }
      }
      // Check for text "Add product" anywhere
      var spans = document.querySelectorAll('span, div');
      for (var i = 0; i < spans.length; i++) {
        if (spans[i].textContent.trim() === 'Add product' && spans[i].children.length === 0) {
          spans[i].scrollIntoView({ behavior: 'instant', block: 'center' });
          var rect = spans[i].getBoundingClientRect();
          return JSON.stringify({
            text: 'span: Add product',
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            w: rect.width,
            h: rect.height
          });
        }
      }
      return 'still not found';
    })()
  `);
  console.log('\nAdd product:', addProductBtn);

  if (addProductBtn !== 'still not found') {
    const { x, y } = JSON.parse(addProductBtn);
    console.log('CDP clicking at (' + x + ', ' + y + ')');
    await c.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await sleep(50);
    await c.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    await sleep(3000);

    // Check
    let text = await c.ev(`document.body.innerText.substring(0, 1000)`);
    console.log('\nAfter click:', text.substring(0, 500));
  } else {
    // Use CDP scroll to scroll within a specific area
    console.log('\nTrying scroll via mouse wheel at (200, 400)');
    for (let i = 0; i < 10; i++) {
      await c.send('Input.dispatchMouseEvent', {
        type: 'mouseWheel',
        x: 200,
        y: 400,
        deltaX: 0,
        deltaY: 200
      });
      await sleep(200);
    }
    await sleep(500);

    // Look again
    const afterScroll = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        var result = [];
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim();
          var rect = btns[i].getBoundingClientRect();
          if ((t.includes('Add') || t.includes('Cancel')) && rect.width > 0) {
            result.push({ text: t.substring(0, 30), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
        }
        return JSON.stringify(result);
      })()
    `);
    console.log('Buttons after wheel scroll:', afterScroll);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
