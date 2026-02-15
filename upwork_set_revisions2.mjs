// Set revisions via dropdown comboboxes: 1, 2, 3
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

async function selectRevision(c, tierIndex, value) {
  // tierIndex: 0=Starter, 1=Standard, 2=Advanced
  const tierNames = ['Starter', 'Standard', 'Advanced'];
  console.log(`\nSetting ${tierNames[tierIndex]} revisions to ${value}...`);

  // Click the combobox to open dropdown
  const opened = await c.ev(`
    (() => {
      var dropdowns = document.querySelectorAll('[data-qa="pricing-package-spec"] .air3-dropdown');
      if (dropdowns.length <= ${tierIndex}) return 'Dropdown not found (have ' + dropdowns.length + ')';
      var toggle = dropdowns[${tierIndex}].querySelector('[role="combobox"]');
      if (!toggle) return 'Combobox not found';
      toggle.click();
      return 'Opened: ' + toggle.querySelector('.air3-dropdown-toggle-label').textContent.trim();
    })()
  `);
  console.log('  Open:', opened);
  await sleep(800);

  // Find and click the option with value
  const selected = await c.ev(`
    (() => {
      var options = document.querySelectorAll('[role="option"], .air3-dropdown-menu-item, .air3-dropdown-menu li');
      var found = [];
      for (var i = 0; i < options.length; i++) {
        if (options[i].offsetParent || window.getComputedStyle(options[i]).display !== 'none') {
          var text = options[i].textContent.trim();
          found.push(text);
          if (text === '${value}') {
            options[i].click();
            return 'Selected: ' + text;
          }
        }
      }
      // If exact match didn't work, try with data-value
      var menuItems = document.querySelectorAll('[data-value="${value}"], [value="${value}"]');
      for (var j = 0; j < menuItems.length; j++) {
        if (menuItems[j].offsetParent) {
          menuItems[j].click();
          return 'Selected via data-value: ${value}';
        }
      }
      return 'Value ${value} not found. Available: ' + found.join(', ');
    })()
  `);
  console.log('  Select:', selected);
  await sleep(500);

  // Verify the value was set
  const verified = await c.ev(`
    (() => {
      var dropdowns = document.querySelectorAll('[data-qa="pricing-package-spec"] .air3-dropdown');
      if (dropdowns.length <= ${tierIndex}) return 'N/A';
      var label = dropdowns[${tierIndex}].querySelector('.air3-dropdown-toggle-label');
      return label ? label.textContent.trim() : 'N/A';
    })()
  `);
  console.log('  Verified:', verified);
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  if (!url.includes('step=Pricing')) {
    await c.ev(`window.location.href = 'https://www.upwork.com/nx/project-dashboard/2021718558562708759?step=Pricing'`);
    await sleep(5000);
  }

  // Set revisions: Starter=1, Standard=2, Advanced=3
  await selectRevision(c, 0, '1');
  await selectRevision(c, 1, '2');
  await selectRevision(c, 2, '3');

  // Verify all three
  console.log('\n=== VERIFICATION ===');
  const allValues = await c.ev(`
    (() => {
      var dropdowns = document.querySelectorAll('[data-qa="pricing-package-spec"] .air3-dropdown');
      var values = [];
      for (var i = 0; i < dropdowns.length; i++) {
        var label = dropdowns[i].querySelector('.air3-dropdown-toggle-label');
        values.push(label ? label.textContent.trim() : 'N/A');
      }
      return JSON.stringify(values);
    })()
  `);
  console.log('Revision values:', allValues);

  // Save
  console.log('\n=== SAVING ===');
  const saveResult = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked Save & Continue';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(saveResult);
  await sleep(5000);

  const finalUrl = await c.ev('window.location.href');
  console.log('Final URL:', finalUrl);

  // Navigate back to dashboard
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/project-dashboard/?step=approved'`);
  await sleep(3000);

  const dashText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
  console.log('\n=== DASHBOARD ===');
  console.log(dashText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
