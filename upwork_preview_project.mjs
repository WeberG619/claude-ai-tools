// Click Preview to view the project listing
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Click More Project Options first
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('More Project Options')) {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(1000);

  // Click Preview from the dropdown
  console.log('=== CLICKING PREVIEW ===');
  const previewClick = await c.ev(`
    (() => {
      // Look in dropdown menus for Preview
      var menuItems = document.querySelectorAll('.air3-dropdown-menu a, .air3-dropdown-menu button, .air3-dropdown-menu-item, [class*="dropdown"] a');
      for (var i = 0; i < menuItems.length; i++) {
        if (menuItems[i].textContent.trim() === 'Preview') {
          var href = menuItems[i].href || '';
          menuItems[i].click();
          return 'Clicked Preview: ' + href;
        }
      }
      // Try any visible element with text "Preview"
      var all = document.querySelectorAll('a, button, span, div');
      for (var j = 0; j < all.length; j++) {
        var t = all[j].textContent.trim();
        if (t === 'Preview' && all[j].offsetParent) {
          all[j].click();
          return 'Clicked Preview (alt): tag=' + all[j].tagName;
        }
      }
      return 'Preview not found';
    })()
  `);
  console.log(previewClick);
  await sleep(5000);

  // Check what page we're on now
  const url = await c.ev('window.location.href');
  console.log('\nURL:', url);

  // Get the full listing text
  const listingText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 5000)`);
  console.log('\n=== PROJECT LISTING ===');
  console.log(listingText);

  // Take a screenshot via CDP
  console.log('\n=== TAKING SCREENSHOT ===');
  const screenshot = await c.send('Page.captureScreenshot', { format: 'png', quality: 90 });
  if (screenshot && screenshot.data) {
    // Save screenshot
    await c.ev(`
      (() => {
        // Can't save from browser, but we have the data
        return 'Screenshot captured: ' + ${JSON.stringify(screenshot.data.length)} + ' chars base64';
      })()
    `);
    // Write to file via Node
    const fs = await import('fs');
    const buffer = Buffer.from(screenshot.data, 'base64');
    fs.writeFileSync('/mnt/d/_CLAUDE-TOOLS/upwork-project-preview.png', buffer);
    console.log('Screenshot saved to /mnt/d/_CLAUDE-TOOLS/upwork-project-preview.png (' + buffer.length + ' bytes)');
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
