// Delete the remaining old file and re-upload the new one
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

  // Step 1: Delete the remaining old file
  console.log('Step 1: Deleting old file...');

  // Click the menu button for the remaining file
  const openMenu = await c.ev(`
    (() => {
      var fileEmbeds = document.querySelectorAll('.react-renderer.node-fileEmbed');
      if (fileEmbeds.length > 0) {
        var embed = fileEmbeds[0]; // Only one left
        var btns = embed.querySelectorAll('button');
        // Click the first button (menu trigger)
        if (btns[0]) {
          btns[0].click();
          return 'Opened menu for: ' + embed.textContent.trim().substring(0, 60);
        }
      }
      return 'No file embeds found';
    })()
  `);
  console.log(openMenu);
  await sleep(1000);

  // Click Delete from the open popover - find the visible one
  const clickDel = await c.ev(`
    (() => {
      // Find all text nodes that say "Delete"
      var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
      var node;
      var results = [];
      while (node = walker.nextNode()) {
        if (node.textContent.trim() === 'Delete' && node.children.length === 0) {
          // Check if this element or its parent is inside a popover that's open
          var parent = node.closest('[data-state="open"], [role="menu"], [class*="popover"]');
          results.push({
            tag: node.tagName,
            hasOpenParent: !!parent,
            rect: node.getBoundingClientRect()
          });
          if (parent || node.getBoundingClientRect().width > 0) {
            node.click();
            // Also try clicking parent
            if (node.parentElement) node.parentElement.click();
            return 'Clicked Delete (tag: ' + node.tagName + ', in open parent: ' + !!parent + ')';
          }
        }
      }
      return 'No clickable Delete found. Results: ' + JSON.stringify(results);
    })()
  `);
  console.log(clickDel);
  await sleep(2000);

  // Check if file is gone
  const check1 = await c.ev(`
    (() => {
      var fileEmbeds = document.querySelectorAll('.react-renderer.node-fileEmbed');
      return 'File embeds remaining: ' + fileEmbeds.length;
    })()
  `);
  console.log(check1);

  // Step 2: Upload the new file
  console.log('\\nStep 2: Uploading new file...');

  const doc = await c.send('DOM.getDocument', {});
  const fileInputNode = await c.send('DOM.querySelector', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"]'
  });
  console.log('File input node:', JSON.stringify(fileInputNode));

  if (fileInputNode.nodeId) {
    await c.send('DOM.setFileInputFiles', {
      nodeId: fileInputNode.nodeId,
      files: ['D:\\_CLAUDE-TOOLS\\RevitStarterKit-v1.0.zip']
    });
    console.log('File set on input');

    await c.ev(`
      (() => {
        var input = document.querySelector('input[type="file"]');
        if (input) {
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return 'change dispatched';
        }
        return 'not found';
      })()
    `);
    await sleep(5000);

    // Check upload
    const afterUpload = await c.ev(`
      (() => {
        var text = document.body.innerText;
        var has274 = text.includes('27.4 KB') || text.includes('27.') || text.includes('28.');
        return 'New file present: ' + has274 + ' | File embeds: ' + document.querySelectorAll('.react-renderer.node-fileEmbed').length;
      })()
    `);
    console.log('After upload:', afterUpload);
  }

  // Step 3: Save
  console.log('\\nStep 3: Saving...');
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

  const result = await c.ev(`document.body.innerText.substring(0, 800)`);
  console.log('Result:', result.substring(0, 500));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
