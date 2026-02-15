// Set revisions to 1, 2, 3 for each tier
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

  // Inspect the revision row structure
  console.log('=== REVISION ROW HTML ===');
  const revisionHTML = await c.ev(`
    (() => {
      // Find "Number of Revisions" label and its parent row
      var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      var node;
      while (node = walker.nextNode()) {
        if (node.textContent.trim() === 'Number of Revisions') {
          var row = node.parentElement;
          // Go up to find the row container
          for (var i = 0; i < 3; i++) {
            if (row.parentElement) row = row.parentElement;
          }
          return row.outerHTML.substring(0, 3000);
        }
      }
      return 'Not found';
    })()
  `);
  console.log(revisionHTML);

  // Find the 3 revision divs that show "0"
  console.log('\n=== REVISION CONTROLS ===');
  const revControls = await c.ev(`
    (() => {
      // Find the revision row
      var allDivs = document.querySelectorAll('div');
      var revRow = null;
      for (var i = 0; i < allDivs.length; i++) {
        if (allDivs[i].getAttribute('aria-label') && allDivs[i].getAttribute('aria-label').includes('Revisions')) {
          var result = {
            ariaLabel: allDivs[i].getAttribute('aria-label'),
            text: allDivs[i].textContent.trim(),
            role: allDivs[i].getAttribute('role') || '',
            tag: allDivs[i].tagName,
            classes: (typeof allDivs[i].className === 'string' ? allDivs[i].className : '').substring(0, 80),
            childCount: allDivs[i].children.length,
            innerHTML: allDivs[i].innerHTML.substring(0, 300)
          };
          // Don't return yet, collect all
          if (!revRow) revRow = [];
          revRow.push(result);
        }
      }
      return JSON.stringify(revRow || 'None found', null, 2);
    })()
  `);
  console.log(revControls);

  // Try clicking on the first "0" revision control to see what happens
  console.log('\n=== CLICKING FIRST REVISION CONTROL ===');
  const clickResult = await c.ev(`
    (() => {
      var allDivs = document.querySelectorAll('div');
      var revDivs = [];
      for (var i = 0; i < allDivs.length; i++) {
        var aria = allDivs[i].getAttribute('aria-label') || '';
        if (aria.includes('Number of Revisions') && aria.includes('Tier')) {
          revDivs.push(allDivs[i]);
        }
      }

      if (revDivs.length === 0) {
        // Try finding by text content - look for divs that show just "0" near revision section
        var revLabel = null;
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        var node;
        while (node = walker.nextNode()) {
          if (node.textContent.trim() === 'Number of Revisions') {
            revLabel = node.parentElement;
            break;
          }
        }
        if (revLabel) {
          // The row container
          var row = revLabel.closest('[class*="grid"]') || revLabel.parentElement.parentElement;
          // Find child divs with "0"
          var zeros = row.querySelectorAll('div');
          for (var k = 0; k < zeros.length; k++) {
            if (zeros[k].textContent.trim() === '0' && zeros[k].children.length === 0) {
              revDivs.push(zeros[k]);
            }
          }
        }
      }

      if (revDivs.length > 0) {
        // Click the first one
        revDivs[0].click();
        return JSON.stringify({
          found: revDivs.length,
          clicked: 'first',
          ariaLabel: revDivs[0].getAttribute('aria-label') || 'none',
          parentHTML: revDivs[0].parentElement.outerHTML.substring(0, 500)
        });
      }
      return JSON.stringify({ found: 0 });
    })()
  `);
  console.log(clickResult);
  await sleep(1000);

  // Check if anything changed (dropdown, input, etc.)
  const afterClick = await c.ev(`
    (() => {
      // Check for new inputs or dropdowns
      var newInputs = document.querySelectorAll('input[type="number"]:not([id*="days"]):not([id*="currency"])');
      var result = [];
      for (var i = 0; i < newInputs.length; i++) {
        if (newInputs[i].offsetParent) {
          result.push({
            type: newInputs[i].type,
            id: newInputs[i].id || '',
            value: newInputs[i].value,
            ariaLabel: newInputs[i].getAttribute('aria-label') || ''
          });
        }
      }
      // Check for role=listbox or options
      var listboxes = document.querySelectorAll('[role="listbox"], [role="option"]');
      var opts = [];
      for (var j = 0; j < listboxes.length; j++) {
        if (listboxes[j].offsetParent) {
          opts.push({
            role: listboxes[j].getAttribute('role'),
            text: listboxes[j].textContent.trim().substring(0, 40)
          });
        }
      }
      // Check for +/- buttons
      var plusMinus = document.querySelectorAll('button');
      var stepBtns = [];
      for (var k = 0; k < plusMinus.length; k++) {
        var t = plusMinus[k].textContent.trim();
        if ((t === '+' || t === '-' || t === 'increase' || t === 'decrease' ||
             plusMinus[k].getAttribute('aria-label')?.includes('increase') ||
             plusMinus[k].getAttribute('aria-label')?.includes('decrease') ||
             plusMinus[k].getAttribute('aria-label')?.includes('add') ||
             plusMinus[k].getAttribute('aria-label')?.includes('subtract')) && plusMinus[k].offsetParent) {
          stepBtns.push({
            text: t.substring(0, 20),
            ariaLabel: plusMinus[k].getAttribute('aria-label') || '',
            classes: (typeof plusMinus[k].className === 'string' ? plusMinus[k].className : '').substring(0, 60)
          });
        }
      }
      return JSON.stringify({ numberInputs: result, listboxes: opts, stepButtons: stepBtns }, null, 2);
    })()
  `);
  console.log('\nAfter click:', afterClick);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
