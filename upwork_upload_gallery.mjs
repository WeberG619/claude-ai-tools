// Upload gallery assets to Upwork Project Catalog draft
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Check current page state
  console.log('=== CURRENT PAGE STATE ===');
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // If not on gallery step, navigate there
  if (!url.includes('step=Gallery')) {
    console.log('Navigating to Gallery step...');
    await c.send('Page.navigate', { url: 'https://www.upwork.com/nx/project-dashboard/2021718558562708759?step=Gallery' });
    await sleep(5000);
  }

  const pageText = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 1500)');
  console.log(pageText);

  // Find all file inputs
  console.log('\n=== FILE INPUTS ===');
  const fileInputs = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          index: i,
          accept: inputs[i].accept || '',
          multiple: inputs[i].multiple,
          id: inputs[i].id || '',
          name: inputs[i].name || '',
          classes: inputs[i].className.substring(0, 60)
        });
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('File inputs:', fileInputs);

  // Get DOM document for file upload
  const doc = await c.send('DOM.getDocument', { depth: -1 });

  // Find image file inputs
  const imageInputs = await c.send('DOM.querySelectorAll', {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"]'
  });
  console.log('File input nodeIds:', JSON.stringify(imageInputs));

  if (!imageInputs.nodeIds || imageInputs.nodeIds.length === 0) {
    console.log('No file inputs found! Looking for upload area...');

    // Check for drag-drop areas or upload buttons
    const uploadArea = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button, [role="button"], label');
        var uploads = [];
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim().toLowerCase();
          if (btns[i].offsetParent && (t.includes('upload') || t.includes('add') || t.includes('browse') || t.includes('image') || t.includes('file') || t.includes('drag'))) {
            uploads.push({ text: btns[i].textContent.trim().substring(0, 60), tag: btns[i].tagName });
          }
        }
        // Also look for drop zones
        var zones = document.querySelectorAll('[class*="drop"], [class*="upload"], [class*="drag"]');
        var zoneInfo = [];
        for (var j = 0; j < zones.length; j++) {
          zoneInfo.push({ class: zones[j].className.substring(0, 60), tag: zones[j].tagName });
        }
        return JSON.stringify({ buttons: uploads, zones: zoneInfo });
      })()
    `);
    console.log('Upload elements:', uploadArea);

    c.close();
    process.exit(0);
  }

  // Windows paths for the files (Chrome runs on Windows)
  const coverPath = 'D:\\_CLAUDE-TOOLS\\revit-plugin-cover.png';
  const pdfPath = 'D:\\_CLAUDE-TOOLS\\revit-plugin-services.pdf';
  const videoPath = 'D:\\_CLAUDE-TOOLS\\revit-plugin-promo.mp4';

  // Try uploading cover image first
  console.log('\n=== UPLOADING COVER IMAGE ===');
  for (const nodeId of imageInputs.nodeIds) {
    try {
      // Get attributes to understand which input this is
      const attrs = await c.send('DOM.getAttributes', { nodeId });
      console.log('Input attrs:', JSON.stringify(attrs));

      // Check accept attribute
      const acceptIdx = attrs.attributes.indexOf('accept');
      const accept = acceptIdx >= 0 ? attrs.attributes[acceptIdx + 1] : '';
      console.log('Accept:', accept);

      if (accept.includes('image') || accept.includes('*') || accept === '') {
        // Upload the cover image
        await c.send('DOM.setFileInputFiles', {
          files: [coverPath],
          nodeId: nodeId
        });
        console.log('Set cover image on nodeId:', nodeId);
        await sleep(3000);

        // Check if upload registered
        const afterUpload = await c.ev(`
          (() => {
            var imgs = document.querySelectorAll('img');
            var blobs = [];
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].src && (imgs[i].src.includes('blob:') || imgs[i].src.includes('upwork'))) {
                blobs.push(imgs[i].src.substring(0, 80));
              }
            }
            var text = (document.querySelector('main') || document.body).innerText;
            var hasError = text.includes('at least one');
            return JSON.stringify({ blobs, hasError, excerpt: text.substring(0, 500) });
          })()
        `);
        console.log('After upload:', afterUpload);
      }

      if (accept.includes('video') || accept.includes('*')) {
        // Upload the video
        console.log('\n=== UPLOADING VIDEO ===');
        await c.send('DOM.setFileInputFiles', {
          files: [videoPath],
          nodeId: nodeId
        });
        console.log('Set video on nodeId:', nodeId);
        await sleep(3000);
      }

      if (accept.includes('pdf') || accept.includes('application') || accept.includes('*')) {
        // Upload the PDF
        console.log('\n=== UPLOADING PDF ===');
        await c.send('DOM.setFileInputFiles', {
          files: [pdfPath],
          nodeId: nodeId
        });
        console.log('Set PDF on nodeId:', nodeId);
        await sleep(3000);
      }
    } catch (e) {
      console.log('Error with nodeId', nodeId, ':', e.message);
    }
  }

  await sleep(3000);

  // Final state check
  console.log('\n=== FINAL STATE ===');
  const finalState = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(finalState);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
