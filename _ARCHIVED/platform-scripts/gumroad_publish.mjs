// Publish the Gumroad product - click through remaining steps
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

  // Step 1: Click "Publish and continue" on Content page
  console.log('Step: Content → Publish and continue');
  let clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Publish and continue')) {
          btns[i].click();
          return 'Clicked';
        }
      }
      // Try Skip for now
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Skip')) {
          btns[i].click();
          return 'Skipped';
        }
      }
      return 'not found';
    })()
  `);
  console.log(clicked);
  await sleep(5000);

  let url = await c.ev('window.location.href');
  console.log('URL:', url);
  let text = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('Page:', text.substring(0, 800));

  // Step 2: Handle Receipt page (if we're on it)
  if (url.includes('receipt') || text.includes('Receipt')) {
    console.log('\n--- Receipt page ---');
    clicked = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim();
          if (t.includes('Publish') || t.includes('Save') || t.includes('continue')) {
            btns[i].click();
            return 'Clicked: ' + t;
          }
        }
        return 'not found';
      })()
    `);
    console.log(clicked);
    await sleep(5000);
    url = await c.ev('window.location.href');
    console.log('URL:', url);
    text = await c.ev(`document.body.innerText.substring(0, 1000)`);
    console.log('Page:', text.substring(0, 500));
  }

  // Step 3: Handle Share page (if we're on it)
  if (url.includes('share') || text.includes('Share')) {
    console.log('\n--- Share page ---');
    // Check what's here
    console.log(text.substring(0, 800));

    // Look for publish/complete button
    clicked = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button, a');
        var result = [];
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent) {
            var t = btns[i].textContent.trim();
            if (t.length > 0 && t.length < 40) {
              result.push({ text: t, tag: btns[i].tagName, href: btns[i].href || '' });
            }
          }
        }
        return JSON.stringify(result.slice(0, 20));
      })()
    `);
    console.log('Buttons:', clicked);
  }

  // Check if product is now published
  console.log('\n=== CHECKING PRODUCT STATUS ===');
  await c.ev(`window.location.href = 'https://gumroad.com/products'`);
  await sleep(3000);
  const prodText = await c.ev(`document.body.innerText.substring(0, 1500)`);
  console.log(prodText.substring(0, 800));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
