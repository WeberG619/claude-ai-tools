// Upload the starter kit zip to Gumroad product content
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
      // Also enable DOM for file upload
      const mid2 = id++;
      pending.set(mid2, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid2, method: 'DOM.enable', params: {} }));
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

  // Navigate to the product content page
  console.log('Navigating to product content...');
  await c.ev(`window.location.href = 'https://gumroad.com/products/iukfn/edit/content'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Find the file input
  const fileInputInfo = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          name: inputs[i].name,
          accept: inputs[i].accept,
          multiple: inputs[i].multiple,
          id: inputs[i].id
        });
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('File inputs:', fileInputInfo);

  // Get the DOM node ID for the file input
  const doc = await c.send('DOM.getDocument', {});
  const fileInputNode = await c.send('DOM.querySelector', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"][name="file"]'
  });
  console.log('File input node:', JSON.stringify(fileInputNode));

  if (fileInputNode.nodeId) {
    // Upload the file
    console.log('Uploading RevitStarterKit-v1.0.zip...');
    await c.send('DOM.setFileInputFiles', {
      nodeId: fileInputNode.nodeId,
      files: ['D:\\_CLAUDE-TOOLS\\RevitStarterKit-v1.0.zip']
    });
    console.log('File set on input');

    // Trigger change event
    await c.ev(`
      (() => {
        var input = document.querySelector('input[type="file"][name="file"]');
        if (input) {
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return 'change dispatched';
        }
        return 'not found';
      })()
    `);
    await sleep(5000);

    // Check if upload appeared
    const afterUpload = await c.ev(`document.body.innerText.substring(0, 2000)`);
    console.log('\nAfter upload:', afterUpload.substring(0, 800));
  }

  // Save
  console.log('\nSaving...');
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

  const result = await c.ev(`document.body.innerText.substring(0, 500)`);
  console.log('Result:', result.substring(0, 300));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
