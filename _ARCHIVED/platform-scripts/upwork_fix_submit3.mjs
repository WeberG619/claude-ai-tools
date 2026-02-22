// Fix rate increase dropdowns and resubmit
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
    const nav = async (url) => { await send('Page.navigate', { url }); await sleep(5000); };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Should still be on the proposal page with errors
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Check the exact errors shown after submit
  console.log('\n=== FINDING ALL ERRORS ===');
  const allErrors = await c.ev(`
    (() => {
      const errorEls = [...document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"], [class*="danger"], [aria-invalid="true"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
        .map(el => ({
          text: el.textContent.trim(),
          tag: el.tagName,
          class: el.className?.substring?.(0, 60) || '',
          id: el.id
        }));
      return JSON.stringify(errorEls);
    })()
  `);
  console.log(allErrors);

  // Get the rate increase section HTML
  console.log('\n=== RATE INCREASE SECTION ===');
  const rateIncHTML = await c.ev(`
    (() => {
      // Find "Schedule a rate increase" text
      const allEls = [...document.querySelectorAll('*')];
      const scheduleEl = allEls.find(el =>
        el.textContent.includes('Schedule a rate increase') &&
        el.children.length === 0
      );
      if (!scheduleEl) return 'Schedule text not found';

      // Go up to find the section
      let section = scheduleEl;
      for (let i = 0; i < 5; i++) {
        if (section.parentElement) section = section.parentElement;
      }

      // Find all interactive elements in this section
      const dropdowns = [...section.querySelectorAll('[role="combobox"]')]
        .map(d => ({
          text: d.textContent.trim(),
          ariaExpanded: d.getAttribute('aria-expanded'),
          ariaLabelledBy: d.getAttribute('aria-labelledby'),
          class: d.className.substring(0, 80),
          outerHTML: d.outerHTML.substring(0, 200)
        }));

      const checkboxes = [...section.querySelectorAll('input[type="checkbox"]')]
        .map(c => ({
          checked: c.checked,
          label: c.closest('label')?.textContent?.trim()?.substring(0, 60),
          id: c.id
        }));

      const toggles = [...section.querySelectorAll('[class*="toggle"], [class*="switch"]')]
        .map(t => ({
          text: t.textContent.trim().substring(0, 40),
          class: t.className.substring(0, 60)
        }));

      return JSON.stringify({
        sectionText: section.innerText.substring(0, 500),
        dropdowns,
        checkboxes,
        toggles
      });
    })()
  `);
  console.log(rateIncHTML);

  // Try clicking the first frequency dropdown
  console.log('\n=== SETTING FREQUENCY ===');
  const freqClick = await c.ev(`
    (() => {
      const dropdowns = [...document.querySelectorAll('[role="combobox"]')].filter(d => d.offsetParent);
      // Find the one that says "Select a frequency"
      const freqDD = dropdowns.find(d => d.textContent.trim().includes('Select a frequency'));
      if (freqDD) {
        freqDD.click();
        return 'Clicked frequency dropdown';
      }
      return 'Frequency dropdown not found. Available: ' + dropdowns.map(d => d.textContent.trim().substring(0, 30)).join(' | ');
    })()
  `);
  console.log(freqClick);
  await sleep(1000);

  // Check what options appeared
  const freqOptions = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"], [role="menuitem"], [class*="dropdown-item"]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          text: el.textContent.trim(),
          value: el.getAttribute('value') || el.dataset?.value,
          role: el.getAttribute('role')
        }));
      // Also check for ul li
      const listItems = [...document.querySelectorAll('[role="listbox"] li, [class*="dropdown-menu"] li')]
        .filter(el => el.offsetParent)
        .map(el => el.textContent.trim().substring(0, 40));
      return JSON.stringify({ options, listItems });
    })()
  `);
  console.log('Frequency options:', freqOptions);

  // Select "None" or first frequency option if available
  const freqSelected = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent);

      // Look for "None" or "No increase" first
      let target = options.find(o => o.textContent.trim().toLowerCase().includes('none') || o.textContent.trim().toLowerCase().includes('no '));
      if (!target && options.length > 0) {
        // Pick the first non-empty option
        target = options[0];
      }
      if (target) {
        target.click();
        return 'Selected: ' + target.textContent.trim();
      }
      return 'No options to select';
    })()
  `);
  console.log('Freq selected:', freqSelected);
  await sleep(1000);

  // Now set percent dropdown
  console.log('\n=== SETTING PERCENT ===');
  const pctClick = await c.ev(`
    (() => {
      const dropdowns = [...document.querySelectorAll('[role="combobox"]')].filter(d => d.offsetParent);
      const pctDD = dropdowns.find(d => d.textContent.trim().includes('Select a percent'));
      if (pctDD) {
        pctDD.click();
        return 'Clicked percent dropdown';
      }
      return 'Percent dropdown not found. Available: ' + dropdowns.map(d => d.textContent.trim().substring(0, 30)).join(' | ');
    })()
  `);
  console.log(pctClick);
  await sleep(1000);

  const pctOptions = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent)
        .map(el => el.textContent.trim());
      return JSON.stringify(options.slice(0, 10));
    })()
  `);
  console.log('Percent options:', pctOptions);

  const pctSelected = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"], [role="menuitem"]')]
        .filter(el => el.offsetParent);
      // Select a small percentage like 5%
      let target = options.find(o => o.textContent.trim().includes('5%'));
      if (!target && options.length > 0) target = options[0];
      if (target) {
        target.click();
        return 'Selected: ' + target.textContent.trim();
      }
      return 'No options';
    })()
  `);
  console.log('Pct selected:', pctSelected);
  await sleep(1000);

  // Check errors again
  const errorsNow = await c.ev(`
    (() => {
      const errors = [...document.querySelectorAll('[class*="error"], [role="alert"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim());
      return JSON.stringify(errors);
    })()
  `);
  console.log('\nErrors now:', errorsNow);

  // Try submit again
  console.log('\n=== SUBMITTING ===');
  const sent = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (btn && !btn.disabled) {
        btn.click();
        return 'Clicked: ' + btn.textContent.trim();
      }
      return btn ? 'Disabled' : 'Not found';
    })()
  `);
  console.log(sent);
  await sleep(8000);

  const result = await c.ev(`
    (() => {
      const url = window.location.href;
      const text = (document.querySelector('main') || document.body).innerText.substring(0, 1000);
      return JSON.stringify({ url, text });
    })()
  `);
  console.log('\nResult:', result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
