// Delete the old 24.9KB file from Gumroad - v2
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

  // First, let's find and open the popover for the 24.9KB file
  const openMenu = await c.ev(`
    (() => {
      var fileEmbeds = document.querySelectorAll('.react-renderer.node-fileEmbed');
      for (var i = 0; i < fileEmbeds.length; i++) {
        var text = fileEmbeds[i].textContent;
        if (text.includes('24.9 KB')) {
          // Find the three-dot menu button
          var btns = fileEmbeds[i].querySelectorAll('button');
          // Click the LAST button which is usually the overflow menu
          var lastBtn = btns[btns.length - 1];
          if (lastBtn) {
            lastBtn.click();
            return 'Clicked last button of 24.9 KB file embed: "' + lastBtn.textContent.trim().substring(0, 20) + '"';
          }
          return 'No buttons in 24.9 KB embed';
        }
      }
      return 'No 24.9 KB file found';
    })()
  `);
  console.log(openMenu);
  await sleep(1000);

  // Now examine what's in the popover and find Delete
  const menuItems = await c.ev(`
    (() => {
      // Get all elements with text "Delete"
      var all = document.querySelectorAll('*');
      var result = [];
      for (var i = 0; i < all.length; i++) {
        if (all[i].textContent.trim() === 'Delete' && all[i].children.length === 0) {
          result.push({
            tag: all[i].tagName,
            className: all[i].className.substring(0, 80),
            role: all[i].getAttribute('role'),
            visible: !!all[i].offsetParent,
            parentTag: all[i].parentElement ? all[i].parentElement.tagName : 'none',
            parentClass: all[i].parentElement ? all[i].parentElement.className.substring(0, 50) : 'none',
            idx: i
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('Delete elements:', menuItems);

  // Click the last visible Delete element (the one for 24.9 KB file)
  const clickDelete = await c.ev(`
    (() => {
      var all = document.querySelectorAll('*');
      var deleteEls = [];
      for (var i = 0; i < all.length; i++) {
        if (all[i].textContent.trim() === 'Delete' && all[i].children.length === 0) {
          deleteEls.push(all[i]);
        }
      }
      // Click the last one (belongs to the 24.9 KB file which is the second/last file)
      if (deleteEls.length > 0) {
        var el = deleteEls[deleteEls.length - 1];
        el.click();
        return 'Clicked Delete #' + (deleteEls.length - 1) + ' (tag: ' + el.tagName + ', parent: ' + el.parentElement.textContent.trim().substring(0, 50) + ')';
      }
      return 'No Delete elements found';
    })()
  `);
  console.log(clickDelete);
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

  // Check if old file is gone
  const check = await c.ev(`
    (() => {
      var text = document.body.innerText;
      var has249 = text.includes('24.9 KB');
      var has274 = text.includes('27.4 KB');
      return '27.4 KB present: ' + has274 + ', 24.9 KB present: ' + has249;
    })()
  `);
  console.log('File check:', check);

  const result = await c.ev(`document.body.innerText.substring(0, 500)`);
  console.log('Result:', result.substring(0, 400));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
