// Delete the old 24.9KB file from Gumroad product content
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

  // Find the 24.9 KB file container and click its menu button
  const clicked = await c.ev(`
    (() => {
      // Find all file embed containers
      var fileEmbeds = document.querySelectorAll('.react-renderer.node-fileEmbed');
      for (var i = 0; i < fileEmbeds.length; i++) {
        var text = fileEmbeds[i].textContent;
        if (text.includes('24.9 KB')) {
          // Find the menu trigger button (button with popover)
          var btns = fileEmbeds[i].querySelectorAll('button');
          for (var j = 0; j < btns.length; j++) {
            // The menu trigger is usually a small icon button
            var ariaHas = btns[j].getAttribute('aria-haspopup');
            var dataSt = btns[j].getAttribute('data-state');
            if (ariaHas || btns[j].textContent.trim() === '') {
              btns[j].click();
              return 'Clicked menu button for 24.9 KB file (btn ' + j + ', aria-haspopup=' + ariaHas + ')';
            }
          }
          return 'No menu button found in 24.9 KB container';
        }
      }
      return 'No 24.9 KB file found';
    })()
  `);
  console.log(clicked);
  await sleep(1000);

  // Now find and click "Delete" in the popover menu
  const deleted = await c.ev(`
    (() => {
      // Look for visible menu items
      var items = document.querySelectorAll('[role="menuitem"], [role="option"], button, a');
      for (var i = 0; i < items.length; i++) {
        var t = items[i].textContent.trim();
        if (t === 'Delete' && items[i].offsetParent) {
          items[i].click();
          return 'Clicked Delete';
        }
      }
      // Also check popovers/dropdowns
      var menus = document.querySelectorAll('[data-state="open"], [role="menu"], .popover');
      var menuTexts = [];
      for (var i = 0; i < menus.length; i++) {
        menuTexts.push(menus[i].textContent.trim().substring(0, 100));
      }
      return 'Delete not found. Open menus: ' + JSON.stringify(menuTexts);
    })()
  `);
  console.log(deleted);
  await sleep(2000);

  // Save changes
  const saved = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Save changes')) {
          btns[i].click();
          return 'Clicked: Save changes';
        }
      }
      return 'not found';
    })()
  `);
  console.log(saved);
  await sleep(3000);

  // Check result
  const text = await c.ev(`document.body.innerText.substring(0, 1000)`);
  console.log('Result:', text.substring(0, 500));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
