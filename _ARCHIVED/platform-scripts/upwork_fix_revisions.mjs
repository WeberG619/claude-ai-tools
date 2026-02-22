// Fix revisions to 1, 2, 3 for each tier
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

  // Navigate to Pricing step
  console.log('=== NAVIGATING TO PRICING ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/project-dashboard/2021718558562708759?step=Pricing'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Get page content to understand the pricing form
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log('\n=== PAGE STATE ===');
  console.log(pageText);

  // Find all revision-related inputs/selects/dropdowns
  console.log('\n=== FINDING REVISION FIELDS ===');
  const revisionFields = await c.ev(`
    (() => {
      // Look for anything related to "revision"
      var allEls = document.querySelectorAll('input, select, [role="combobox"], [role="spinbutton"], button');
      var result = [];
      for (var i = 0; i < allEls.length; i++) {
        var el = allEls[i];
        if (!el.offsetParent) continue;
        var label = el.closest('label') || el.parentElement;
        var labelText = label ? label.textContent.trim().substring(0, 80) : '';
        var ariaLabel = el.getAttribute('aria-label') || '';
        var name = el.name || '';
        var id = el.id || '';

        if (labelText.toLowerCase().includes('revis') || ariaLabel.toLowerCase().includes('revis') ||
            name.toLowerCase().includes('revis') || id.toLowerCase().includes('revis') ||
            el.getAttribute('data-qa')?.includes('revis')) {
          result.push({
            tag: el.tagName,
            type: el.type || '',
            id: id,
            name: name,
            value: el.value || '',
            ariaLabel: ariaLabel,
            labelText: labelText.substring(0, 80),
            dataQa: el.getAttribute('data-qa') || '',
            classes: (typeof el.className === 'string' ? el.className : '').substring(0, 60)
          });
        }
      }

      // Also look for inputs near "Number of Revisions" text
      var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      var node;
      var revisionSections = [];
      while (node = walker.nextNode()) {
        if (node.textContent.includes('Revisions') || node.textContent.includes('revisions')) {
          var parent = node.parentElement;
          for (var k = 0; k < 3; k++) {
            if (parent.parentElement) parent = parent.parentElement;
          }
          var inputs = parent.querySelectorAll('input, select, [role="combobox"], button');
          for (var m = 0; m < inputs.length; m++) {
            if (inputs[m].offsetParent) {
              revisionSections.push({
                tag: inputs[m].tagName,
                type: inputs[m].type || '',
                id: inputs[m].id || '',
                value: inputs[m].value || '',
                text: inputs[m].textContent?.trim().substring(0, 40) || '',
                dataQa: inputs[m].getAttribute('data-qa') || ''
              });
            }
          }
        }
      }

      return JSON.stringify({ directMatches: result, nearRevisionText: revisionSections }, null, 2);
    })()
  `);
  console.log(revisionFields);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
