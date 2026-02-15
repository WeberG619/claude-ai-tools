// Check what's in the Sample Documents section
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

  // Get all document items in the Sample Documents section
  console.log('=== SAMPLE DOCUMENTS ITEMS ===');
  const docs = await c.ev(`
    (() => {
      // Find the section container
      var h4s = document.querySelectorAll('h4');
      var sampleSection = null;
      for (var i = 0; i < h4s.length; i++) {
        if (h4s[i].textContent.includes('Sample Documents')) {
          sampleSection = h4s[i].parentElement;
          break;
        }
      }
      if (!sampleSection) return 'Section not found';

      // Find all gallery items in this section
      var items = sampleSection.querySelectorAll('[data-qa], .gallery-item, img');
      var result = [];
      for (var j = 0; j < items.length; j++) {
        if (items[j].tagName === 'IMG') {
          result.push({
            type: 'image',
            src: items[j].src,
            alt: items[j].alt || ''
          });
        }
      }

      // Also check for any IDs
      var idItems = sampleSection.querySelectorAll('[id]');
      var ids = [];
      for (var k = 0; k < idItems.length; k++) {
        ids.push({
          id: idItems[k].id,
          tag: idItems[k].tagName,
          classes: (typeof idItems[k].className === 'string' ? idItems[k].className : '').substring(0, 60)
        });
      }

      // Check grid container content
      var grid = sampleSection.querySelector('.air3-grid-container');
      var gridChildren = grid ? grid.children.length : 0;

      // Check for upload/browse area in the section
      var hasUpload = !!sampleSection.querySelector('.video-upload, .video-upload-content, input[type="file"]');

      return JSON.stringify({
        images: result,
        ids: ids,
        gridChildren: gridChildren,
        hasUploadArea: hasUpload,
        fullText: sampleSection.innerText.substring(0, 500)
      }, null, 2);
    })()
  `);
  console.log(docs);

  // Check if the existing items are actually PDFs (maybe the upload went through before)
  console.log('\n=== CHECKING CLOUDINARY IMAGES ===');
  const cloudinaryUrls = await c.ev(`
    (() => {
      var h4s = document.querySelectorAll('h4');
      var sampleSection = null;
      for (var i = 0; i < h4s.length; i++) {
        if (h4s[i].textContent.includes('Sample Documents')) {
          sampleSection = h4s[i].parentElement;
          break;
        }
      }
      if (!sampleSection) return 'Not found';
      var imgs = sampleSection.querySelectorAll('img');
      var urls = [];
      for (var j = 0; j < imgs.length; j++) {
        urls.push(imgs[j].src);
      }
      return JSON.stringify(urls);
    })()
  `);
  console.log(cloudinaryUrls);

  // Check how many document slots are used vs available
  console.log('\n=== DOCUMENT SLOT STATUS ===');
  const slotStatus = await c.ev(`
    (() => {
      var h4s = document.querySelectorAll('h4');
      var sampleSection = null;
      for (var i = 0; i < h4s.length; i++) {
        if (h4s[i].textContent.includes('Sample Documents')) {
          sampleSection = h4s[i].parentElement;
          break;
        }
      }
      if (!sampleSection) return 'Not found';

      var grid = sampleSection.querySelector('.air3-grid-container');
      if (!grid) return 'No grid found';

      var children = grid.children;
      var slots = [];
      for (var k = 0; k < children.length; k++) {
        var child = children[k];
        var hasImage = !!child.querySelector('img');
        var hasUpload = !!child.querySelector('.video-upload-content, input[type="file"]');
        var isUploadSlot = child.textContent.includes('Drag') || child.textContent.includes('browse');
        slots.push({
          index: k,
          hasImage: hasImage,
          isUploadSlot: isUploadSlot,
          hasUpload: hasUpload,
          text: child.textContent.trim().substring(0, 80),
          classes: (typeof child.className === 'string' ? child.className : '').substring(0, 60)
        });
      }

      return JSON.stringify({ totalSlots: children.length, slots: slots }, null, 2);
    })()
  `);
  console.log(slotStatus);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
