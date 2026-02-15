// Upload gallery assets with proper event dispatching
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

async function uploadFile(c, selector, winPath, label) {
  console.log(`\n=== UPLOADING ${label} ===`);

  // Get DOM document
  const doc = await c.send('DOM.getDocument', { depth: -1 });
  const nodes = await c.send('DOM.querySelectorAll', {
    nodeId: doc.root.nodeId,
    selector: selector
  });

  if (!nodes.nodeIds || nodes.nodeIds.length === 0) {
    console.log(`No input found for selector: ${selector}`);
    return false;
  }

  const nodeId = nodes.nodeIds[0];
  console.log(`Found input nodeId: ${nodeId}`);

  // Set the file
  await c.send('DOM.setFileInputFiles', {
    files: [winPath],
    nodeId: nodeId
  });
  console.log('File set via CDP');

  // Now dispatch events via JavaScript to trigger Vue/React handlers
  const eventResult = await c.ev(`
    (() => {
      var input = document.querySelector('${selector}');
      if (!input) return 'Input not found via JS';

      // Check if files were actually set
      if (input.files.length === 0) return 'No files on input after CDP set';

      var fileInfo = input.files[0].name + ' (' + input.files[0].size + ' bytes, ' + input.files[0].type + ')';

      // Dispatch comprehensive events
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));

      return 'Events dispatched. File: ' + fileInfo;
    })()
  `);
  console.log('Event result:', eventResult);

  await sleep(5000);

  // Check for upload progress/completion
  const state = await c.ev(`
    (() => {
      var text = (document.querySelector('main') || document.body).innerText;

      // Look for uploaded image thumbnails
      var imgs = document.querySelectorAll('img[src*="blob:"], img[src*="cloudinary"]');
      var imgSrcs = [];
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].width > 50) imgSrcs.push(imgs[i].src.substring(0, 60));
      }

      // Check for progress bars or upload indicators
      var progressBars = document.querySelectorAll('[role="progressbar"], .progress, [class*="progress"]');

      // Check for "Set as project cover" button indicating upload success
      var hasCoverBtn = text.includes('Set as project cover');

      // Check for delete/remove buttons on uploaded items
      var deleteButtons = document.querySelectorAll('button[aria-label*="delete"], button[aria-label*="remove"]');

      return JSON.stringify({
        imageCount: imgSrcs.length,
        images: imgSrcs,
        progressBars: progressBars.length,
        hasCoverBtn: hasCoverBtn,
        deleteButtons: deleteButtons.length,
        textExcerpt: text.substring(0, 800)
      });
    })()
  `);
  console.log('Upload state:', state);
  return true;
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Ensure we're on gallery step
  const url = await c.ev('window.location.href');
  if (!url.includes('step=Gallery')) {
    await c.send('Page.navigate', { url: 'https://www.upwork.com/nx/project-dashboard/2021718558562708759?step=Gallery' });
    await sleep(5000);
  }

  // Upload image (first file input: accepts images)
  await uploadFile(
    c,
    'input[type="file"][accept*="image"]',
    'D:\\_CLAUDE-TOOLS\\revit-plugin-cover.png',
    'COVER IMAGE'
  );

  // Upload video (second file input: accepts .mp4)
  await uploadFile(
    c,
    'input[type="file"][accept=".mp4"]',
    'D:\\_CLAUDE-TOOLS\\revit-plugin-promo.mp4',
    'VIDEO'
  );

  // Upload PDF (third file input: accepts .pdf)
  await uploadFile(
    c,
    'input[type="file"][accept=".pdf"]',
    'D:\\_CLAUDE-TOOLS\\revit-plugin-services.pdf',
    'PDF DOCUMENT'
  );

  // Final page state
  console.log('\n=== FINAL PAGE STATE ===');
  const finalText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2500)`);
  console.log(finalText);

  // Check for the Continue button being enabled
  const continueBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim() === 'Continue') {
          return { disabled: btns[i].disabled, text: btns[i].textContent.trim() };
        }
      }
      return null;
    })()
  `);
  console.log('Continue button:', JSON.stringify(continueBtn));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
