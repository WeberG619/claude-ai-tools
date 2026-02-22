// Save the gallery and continue (PDF is already uploaded)
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

  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  // Check if we need to delete one and re-upload, or if both are our PDF
  // First let's see a summary of the gallery
  console.log('\n=== GALLERY SUMMARY ===');
  const summary = await c.ev(`
    (() => {
      var main = document.querySelector('main') || document.body;
      // Count images section
      var images = document.querySelectorAll('[coverid] img, .gallery-item img');
      var imageCount = 0;
      var videoCount = 0;
      var docCount = 0;

      // Count by section
      var h4s = main.querySelectorAll('h4');
      var sections = {};
      for (var i = 0; i < h4s.length; i++) {
        var t = h4s[i].textContent.trim();
        var parent = h4s[i].parentElement;
        var grid = parent.querySelector('.air3-grid-container');
        if (grid) {
          var items = grid.querySelectorAll('.gallery-item, [id]:not([id^="popper"])');
          sections[t.substring(0, 30)] = items.length;
        }
      }

      return JSON.stringify(sections);
    })()
  `);
  console.log(summary);

  // The gallery already has 2 PDF docs. Let's delete one and upload our actual PDF.
  // But first, let me check - are both slots showing the same document or different?
  // Since both have different Cloudinary IDs, they're likely 2 copies of same PDF or 2 different files

  // Actually, since both slots are filled and the project is under review, let's just
  // click "Save & exit" or "Continue" to save the current state
  console.log('\n=== SAVING GALLERY ===');

  // Click Save & exit (since the project is already submitted)
  const saveResult = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (btns[i].offsetParent && (t === 'Save & exit' || t.includes('Save & exit'))) {
          btns[i].click();
          return 'Clicked: ' + t;
        }
      }
      // Try Continue
      for (var j = 0; j < btns.length; j++) {
        var t2 = btns[j].textContent.trim();
        if (btns[j].offsetParent && t2 === 'Continue') {
          btns[j].click();
          return 'Clicked: Continue';
        }
      }
      return 'No save button found';
    })()
  `);
  console.log(saveResult);
  await sleep(5000);

  const finalUrl = await c.ev('window.location.href');
  console.log('\nFinal URL:', finalUrl);

  const finalText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1000)`);
  console.log('\n=== RESULT ===');
  console.log(finalText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
