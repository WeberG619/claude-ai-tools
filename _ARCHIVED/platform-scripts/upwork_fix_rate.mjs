// Fix the rate increase dropdowns on the proposal form
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
      if (msg.method === 'Page.javascriptDialogOpening') {
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
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
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Look at the rate increase section more closely
  console.log('=== RATE INCREASE SECTION ===');
  const rateSection = await c.ev(`
    (() => {
      // Find all comboboxes on the page
      var combos = document.querySelectorAll('[role="combobox"]');
      var result = [];
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) {
          var parent = combos[i].closest('.air3-dropdown');
          var toggle = parent ? parent.querySelector('.air3-dropdown-toggle') : null;
          result.push({
            index: i,
            text: combos[i].textContent.trim().substring(0, 50),
            toggleText: toggle ? toggle.textContent.trim().substring(0, 50) : '',
            parentClasses: (parent && typeof parent.className === 'string') ? parent.className.substring(0, 80) : '',
            ariaLabel: combos[i].getAttribute('aria-label') || '',
            ariaExpanded: combos[i].getAttribute('aria-expanded') || ''
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(rateSection);

  // Click the first combobox to see options
  console.log('\n=== CLICKING FIRST DROPDOWN ===');
  await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) {
          combos[i].click();
          return 'Clicked combo ' + i;
        }
      }
      return 'none';
    })()
  `);
  await sleep(500);

  const options1 = await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      var result = [];
      for (var i = 0; i < opts.length; i++) {
        result.push(opts[i].textContent.trim());
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Frequency options:', options1);

  // Select first meaningful option
  const selected1 = await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        var t = opts[i].textContent.trim().toLowerCase();
        if (t.includes('3 month') || t.includes('quarter') || t.includes('6 month') || t.includes('every')) {
          opts[i].click();
          return 'Selected: ' + opts[i].textContent.trim();
        }
      }
      // Just click the first one
      if (opts.length > 0) {
        opts[0].click();
        return 'Selected first: ' + opts[0].textContent.trim();
      }
      return 'no options';
    })()
  `);
  console.log('Selected frequency:', selected1);
  await sleep(500);

  // Now click second combobox
  console.log('\n=== CLICKING SECOND DROPDOWN ===');
  await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      var visible = [];
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) visible.push(combos[i]);
      }
      if (visible.length >= 2) {
        visible[1].click();
        return 'Clicked combo 2';
      }
      return 'no second combo';
    })()
  `);
  await sleep(500);

  const options2 = await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      var result = [];
      for (var i = 0; i < opts.length; i++) {
        result.push(opts[i].textContent.trim());
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Percent options:', options2);

  // Select a small percent
  const selected2 = await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        var t = opts[i].textContent.trim();
        if (t.includes('3%') || t.includes('5%') || t === '3' || t === '5') {
          opts[i].click();
          return 'Selected: ' + t;
        }
      }
      if (opts.length > 0) {
        opts[0].click();
        return 'Selected first: ' + opts[0].textContent.trim();
      }
      return 'no options';
    })()
  `);
  console.log('Selected percent:', selected2);
  await sleep(500);

  // Check if errors are gone
  console.log('\n=== REMAINING ERRORS ===');
  const remainingErrors = await c.ev(`
    (() => {
      var errors = document.querySelectorAll('.air3-form-message-error');
      var result = [];
      for (var i = 0; i < errors.length; i++) {
        if (errors[i].offsetParent) result.push(errors[i].textContent.trim());
      }
      return JSON.stringify(result);
    })()
  `);
  console.log(remainingErrors);

  // Now try submitting
  console.log('\n=== TRYING SUBMIT ===');
  const submitResult = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && !btns[i].disabled && (t.includes('submit') || t.includes('send'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'no submit';
    })()
  `);
  console.log(submitResult);
  await sleep(8000);

  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
  console.log('Result URL:', resultUrl);
  console.log('Result:', resultText.substring(0, 300));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
