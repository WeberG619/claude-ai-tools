// Edit the Autodesk Automation API proposal to fix the amount from $130,130 to $130
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(4);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
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

  // Navigate to the proposal page
  const proposalUrl = 'https://www.upwork.com/nx/proposals/2021740326202302465';
  console.log('Navigating to proposal...');
  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
  await c.ev(`window.location.href = ${JSON.stringify(proposalUrl)}`);
  await sleep(5000);

  // Look for Edit button
  console.log('Looking for Edit button...');
  const editBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, a');
      var found = [];
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t.includes('edit') || t.includes('modify'))) {
          found.push({ text: btns[i].textContent.trim(), tag: btns[i].tagName, href: btns[i].href || '' });
        }
      }
      return JSON.stringify(found);
    })()
  `);
  console.log('Edit buttons:', editBtn);

  // Click the edit proposal link/button
  const clickResult = await c.ev(`
    (() => {
      var els = document.querySelectorAll('a, button');
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim().toLowerCase();
        if (els[i].offsetParent && (t === 'edit proposal' || t === 'edit' || t.includes('edit proposal'))) {
          els[i].click();
          return 'Clicked: ' + els[i].textContent.trim() + ' href=' + (els[i].href || 'none');
        }
      }
      return 'not found';
    })()
  `);
  console.log('Click:', clickResult);
  await sleep(5000);

  const newUrl = await c.ev('window.location.href');
  console.log('URL after edit click:', newUrl);

  // Check the form
  const amountField = await c.ev(`
    (() => {
      var el = document.getElementById('charged-amount-id');
      if (el) return 'found: ' + el.value;
      // Try other amount fields
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && (inputs[i].value.includes('130') || inputs[i].placeholder === '$0.00')) {
          return 'alt: id=' + inputs[i].id + ' val=' + inputs[i].value;
        }
      }
      return 'not found';
    })()
  `);
  console.log('Amount field:', amountField);

  if (amountField.includes('130')) {
    // Focus and fix the amount
    console.log('Fixing amount...');
    await c.ev(`
      (() => {
        var el = document.getElementById('charged-amount-id');
        if (!el) {
          var inputs = document.querySelectorAll('input[type="text"]');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent && inputs[i].value.includes('130')) {
              el = inputs[i]; break;
            }
          }
        }
        if (el) { el.focus(); return 'focused'; }
        return 'not found';
      })()
    `);
    await sleep(200);
    await c.selectAll();
    await sleep(200);
    // Type just "130" - the input should format it
    await c.typeText('130');
    await sleep(500);

    // Tab out to trigger validation
    await c.ev(`
      (() => {
        var el = document.getElementById('charged-amount-id') || document.activeElement;
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'blurred';
      })()
    `);
    await sleep(500);

    // Check new value
    const newAmount = await c.ev(`
      (() => {
        var el = document.getElementById('charged-amount-id');
        if (el) return el.value;
        var inputs = document.querySelectorAll('input[type="text"]');
        for (var i = 0; i < inputs.length; i++) {
          if (inputs[i].offsetParent && inputs[i].value.includes('130')) return inputs[i].value;
        }
        return 'not found';
      })()
    `);
    console.log('New amount:', newAmount);

    // Submit the edit
    await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
    await sleep(500);

    const submitResult = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim().toLowerCase();
          if (btns[i].offsetParent && !btns[i].disabled && (t.includes('update') || t.includes('save') || t.includes('submit') || t.includes('send'))) {
            btns[i].click();
            return 'Clicked: ' + btns[i].textContent.trim();
          }
        }
        return 'no update button';
      })()
    `);
    console.log('Submit:', submitResult);
    await sleep(8000);

    const resultUrl = await c.ev('window.location.href');
    const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
    console.log('Result URL:', resultUrl);
    console.log('Result:', resultText.substring(0, 300));
  } else {
    // Dump the page to see what we have
    const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
    console.log('Page text:', pageText);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
