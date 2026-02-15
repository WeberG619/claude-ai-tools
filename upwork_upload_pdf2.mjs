// Find and use the PDF upload on the gallery page
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

  // Look for the PDF upload section and any clickable elements in it
  console.log('=== FINDING PDF UPLOAD AREA ===');
  const pdfSection = await c.ev(`
    (() => {
      // Look for text "Sample Documents" and find the section
      var allElements = document.querySelectorAll('*');
      var sampleDocSection = null;
      for (var i = 0; i < allElements.length; i++) {
        if (allElements[i].textContent.includes('Sample Documents') && allElements[i].children.length < 20) {
          // Check if this is the heading/container
          var el = allElements[i];
          if (el.tagName === 'H3' || el.tagName === 'H4' || el.tagName === 'H5' || el.tagName === 'SPAN' ||
              el.tagName === 'DIV' || el.tagName === 'P' || el.tagName === 'LABEL' || el.tagName === 'SECTION') {
            if (el.textContent.trim().startsWith('Sample Documents')) {
              sampleDocSection = el;
              break;
            }
          }
        }
      }

      if (!sampleDocSection) return 'Sample Documents section not found';

      // Get the parent container (likely a few levels up)
      var container = sampleDocSection.parentElement;
      for (var j = 0; j < 3; j++) {
        if (container.parentElement) container = container.parentElement;
      }

      // Find all interactive elements in this container
      var interactives = container.querySelectorAll('button, a, input, [role="button"], [class*="upload"], [class*="browse"], [class*="drop"]');
      var result = [];
      for (var k = 0; k < interactives.length; k++) {
        result.push({
          tag: interactives[k].tagName,
          type: interactives[k].type || '',
          text: interactives[k].textContent.trim().substring(0, 60),
          classes: interactives[k].className.substring(0, 80),
          accept: interactives[k].accept || '',
          href: interactives[k].href ? interactives[k].href.substring(0, 80) : ''
        });
      }

      return JSON.stringify({
        sectionTag: sampleDocSection.tagName,
        sectionText: sampleDocSection.textContent.trim().substring(0, 100),
        containerHTML: container.innerHTML.substring(0, 1500),
        interactives: result
      }, null, 2);
    })()
  `);
  console.log(pdfSection);

  // Also check ALL file inputs including hidden ones
  console.log('\n=== ALL FILE INPUTS (including hidden) ===');
  const allFileInputs = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        var parent = inputs[i].parentElement;
        var grandparent = parent ? parent.parentElement : null;
        result.push({
          index: i,
          accept: inputs[i].accept || '',
          visible: !!inputs[i].offsetParent,
          display: window.getComputedStyle(inputs[i]).display,
          parentClasses: parent ? parent.className.substring(0, 60) : '',
          parentText: parent ? parent.textContent.trim().substring(0, 80) : '',
          grandparentText: grandparent ? grandparent.textContent.trim().substring(0, 80) : ''
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(allFileInputs);

  // Scroll down to make sure PDF section is visible
  console.log('\n=== SCROLLING TO PDF SECTION ===');
  await c.ev(`
    (() => {
      // Find the Sample Documents text and scroll to it
      var elements = document.querySelectorAll('*');
      for (var i = 0; i < elements.length; i++) {
        var text = elements[i].textContent.trim();
        if (text.startsWith('Sample Documents') && elements[i].children.length < 5) {
          elements[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
          return 'Scrolled to: ' + elements[i].tagName + ' - ' + text.substring(0, 60);
        }
      }
      return 'Not found';
    })()
  `);
  await sleep(2000);

  // Re-check file inputs after scroll
  const afterScroll = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      return 'Total file inputs: ' + inputs.length + ', accepts: ' + Array.from(inputs).map(i => i.accept).join(' | ');
    })()
  `);
  console.log('After scroll:', afterScroll);

  // Look for any drag-drop zones or browse links for PDFs
  const dropZones = await c.ev(`
    (() => {
      var zones = document.querySelectorAll('[class*="drop"], [class*="upload"], [class*="drag"], [class*="browse"], [class*="document"], [class*="pdf"], [class*="sample"]');
      var result = [];
      for (var i = 0; i < zones.length; i++) {
        if (zones[i].offsetParent || window.getComputedStyle(zones[i]).display !== 'none') {
          result.push({
            tag: zones[i].tagName,
            classes: zones[i].className.substring(0, 80),
            text: zones[i].textContent.trim().substring(0, 100),
            children: zones[i].children.length
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\n=== DROP ZONES / UPLOAD AREAS ===');
  console.log(dropZones);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
