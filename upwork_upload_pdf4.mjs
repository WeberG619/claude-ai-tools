// Find PDF upload section and upload the PDF
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

  // Find the Sample Documents section HTML directly
  console.log('=== SAMPLE DOCUMENTS SECTION ===');
  const sectionHTML = await c.ev(`
    (() => {
      // Find the h4 with "Sample Documents"
      var h4s = document.querySelectorAll('h4');
      for (var i = 0; i < h4s.length; i++) {
        if (h4s[i].textContent.includes('Sample Documents')) {
          // Get the parent div that contains the upload area
          var parent = h4s[i].parentElement;
          return JSON.stringify({
            parentTag: parent.tagName,
            parentClasses: (typeof parent.className === 'string' ? parent.className : '').substring(0, 80),
            parentHTML: parent.outerHTML.substring(0, 3000),
            siblingCount: parent.children.length
          });
        }
      }
      return 'h4 with Sample Documents not found';
    })()
  `);
  console.log(sectionHTML);

  // Also check if there's a "browse" button or upload area for docs
  console.log('\n=== LOOKING FOR PDF BROWSE/UPLOAD ===');
  const browseButtons = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var browses = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim() === 'browse' || btns[i].textContent.trim().includes('Upload') ||
            btns[i].textContent.trim().includes('Add document') || btns[i].textContent.trim().includes('Add PDF')) {
          var nextSibling = btns[i].nextElementSibling;
          var prevSibling = btns[i].previousElementSibling;
          browses.push({
            text: btns[i].textContent.trim(),
            visible: !!btns[i].offsetParent,
            parentText: btns[i].parentElement ? btns[i].parentElement.textContent.trim().substring(0, 80) : '',
            nextInput: nextSibling ? nextSibling.tagName + ':' + (nextSibling.type || '') : '',
            prevInput: prevSibling ? prevSibling.tagName + ':' + (prevSibling.type || '') : ''
          });
        }
      }
      return JSON.stringify(browses, null, 2);
    })()
  `);
  console.log(browseButtons);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
