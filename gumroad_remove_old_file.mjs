// Remove the old 24.9KB file from Gumroad product content
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

  // Check current content page
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Find all file items and their delete/remove buttons
  const fileItems = await c.ev(`
    (() => {
      // Look for file entries - they contain the file name and size
      var items = document.querySelectorAll('[class*="file"], [class*="content"], [class*="item"], [class*="row"]');
      var result = [];
      for (var i = 0; i < items.length; i++) {
        var text = items[i].textContent.trim();
        if (text.includes('24.9 KB') || text.includes('27.4 KB')) {
          // Find buttons/links inside
          var btns = items[i].querySelectorAll('button, a, [role="button"]');
          var btnTexts = [];
          for (var j = 0; j < btns.length; j++) {
            btnTexts.push({ text: btns[j].textContent.trim().substring(0, 30), tag: btns[j].tagName });
          }
          result.push({
            text: text.substring(0, 100),
            buttons: btnTexts,
            className: items[i].className.substring(0, 80)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('File items:', fileItems);

  // Look for all delete/remove/trash icons or buttons
  const allBtns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, [role="button"]');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        var svg = btns[i].querySelector('svg');
        var ariaLabel = btns[i].getAttribute('aria-label') || '';
        if (t.includes('delete') || t.includes('remove') || t.includes('trash') ||
            ariaLabel.toLowerCase().includes('delete') || ariaLabel.toLowerCase().includes('remove') ||
            (svg && btns[i].textContent.trim().length < 3)) {
          result.push({
            text: btns[i].textContent.trim().substring(0, 30),
            ariaLabel: ariaLabel,
            tag: btns[i].tagName,
            visible: !!btns[i].offsetParent,
            idx: i
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\nDelete/remove buttons:', allBtns);

  // Get the full HTML structure around the files
  const fileHtml = await c.ev(`
    (() => {
      // Look for elements that mention the file sizes
      var body = document.body.innerHTML;
      var idx1 = body.indexOf('24.9 KB');
      var idx2 = body.indexOf('27.4 KB');
      var result = '';
      if (idx1 > -1) {
        result += '--- 24.9 KB context ---\\n' + body.substring(Math.max(0, idx1-500), idx1+200) + '\\n\\n';
      }
      if (idx2 > -1) {
        result += '--- 27.4 KB context ---\\n' + body.substring(Math.max(0, idx2-500), idx2+200);
      }
      return result;
    })()
  `);
  console.log('\nHTML context:', fileHtml.substring(0, 2000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
