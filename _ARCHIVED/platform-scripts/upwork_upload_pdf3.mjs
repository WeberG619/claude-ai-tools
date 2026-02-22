// Find PDF upload section HTML and trigger it
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

  // Get the actual HTML around "Sample Documents"
  console.log('=== SAMPLE DOCUMENTS HTML ===');
  const sampleHTML = await c.ev(`
    (() => {
      var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      var node;
      while (node = walker.nextNode()) {
        if (node.textContent.includes('Sample Documents')) {
          // Go up a few levels to get the section
          var section = node.parentElement;
          for (var i = 0; i < 5; i++) {
            if (section.parentElement && section.parentElement.tagName !== 'BODY') {
              section = section.parentElement;
            }
          }
          return section.outerHTML.substring(0, 3000);
        }
      }
      return 'Not found';
    })()
  `);
  console.log(sampleHTML);

  // Look specifically for upload/browse/drag elements near "Sample Documents"
  console.log('\n=== PDF SECTION INTERACTIVE ELEMENTS ===');
  const pdfInteractive = await c.ev(`
    (() => {
      // Find the "Sample Documents" heading
      var headings = document.querySelectorAll('h4, h3, h5, div, span, p');
      var sampleHeading = null;
      for (var i = 0; i < headings.length; i++) {
        var t = headings[i].textContent.trim();
        if (t.startsWith('Sample Documents') && headings[i].children.length < 5) {
          sampleHeading = headings[i];
          break;
        }
      }
      if (!sampleHeading) return 'Heading not found';

      // Get its next siblings and parent's children
      var container = sampleHeading.closest('section') || sampleHeading.closest('div') || sampleHeading.parentElement;

      // Get ALL elements in this container that could be clickable
      var all = container.querySelectorAll('*');
      var result = [];
      for (var j = 0; j < all.length; j++) {
        var el = all[j];
        var tag = el.tagName;
        if (tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || el.getAttribute('role') === 'button' ||
            el.classList.contains('browse') || el.classList.contains('upload') ||
            el.style.cursor === 'pointer' || window.getComputedStyle(el).cursor === 'pointer') {
          result.push({
            tag: tag,
            type: el.type || '',
            text: el.textContent.trim().substring(0, 60),
            classes: el.className.substring(0, 80),
            cursor: window.getComputedStyle(el).cursor
          });
        }
      }

      return JSON.stringify({
        heading: sampleHeading.tagName + ': ' + sampleHeading.textContent.trim().substring(0, 60),
        container: container.tagName + '.' + container.className.substring(0, 40),
        containerText: container.textContent.trim().substring(0, 200),
        containerHTML: container.outerHTML.substring(0, 2000),
        clickable: result
      }, null, 2);
    })()
  `);
  console.log(pdfInteractive);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
