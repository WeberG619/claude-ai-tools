// Check Gumroad Content page and look for file upload
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
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Get full page text
  const text = await c.ev(`document.body.innerText`);
  console.log('Page:', text.substring(0, 2000));

  // Look for file input elements
  const fileInputs = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          id: inputs[i].id || '',
          name: inputs[i].name || '',
          accept: inputs[i].accept || '',
          multiple: inputs[i].multiple
        });
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\nFile inputs:', fileInputs);

  // Look for upload buttons/areas
  const uploadBtns = await c.ev(`
    (() => {
      var els = document.querySelectorAll('button, a, [role="button"]');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim().toLowerCase();
        if (t.includes('upload') || t.includes('file') || t.includes('add') || t.includes('drop')) {
          result.push({ text: els[i].textContent.trim().substring(0, 40), tag: els[i].tagName });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Upload buttons:', uploadBtns);

  // Check all buttons
  const allBtns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var r = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent) {
          r.push(btns[i].textContent.trim().substring(0, 40));
        }
      }
      return JSON.stringify(r);
    })()
  `);
  console.log('All buttons:', allBtns);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
