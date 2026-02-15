// Check checkbox states and submit
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

  // Check checkbox states
  console.log('=== CHECKBOX STATES ===');
  const checkboxes = await c.ev(`
    (() => {
      var cbs = document.querySelectorAll('input[type="checkbox"]');
      var result = [];
      for (var i = 0; i < cbs.length; i++) {
        if (cbs[i].offsetParent) {
          var label = cbs[i].closest('label') || cbs[i].parentElement;
          result.push({
            checked: cbs[i].checked,
            labelText: label ? label.textContent.trim().substring(0, 60) : '',
            index: i
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log(checkboxes);

  // Make sure both are checked
  const ensureChecked = await c.ev(`
    (() => {
      var cbs = document.querySelectorAll('input[type="checkbox"]');
      var results = [];
      for (var i = 0; i < cbs.length; i++) {
        if (cbs[i].offsetParent) {
          if (!cbs[i].checked) {
            cbs[i].click();
            results.push('Checked index ' + i);
          } else {
            results.push('Already checked index ' + i);
          }
        }
      }
      return results.join(', ');
    })()
  `);
  console.log('Ensure checked:', ensureChecked);
  await sleep(1000);

  // Verify submit button state
  const submitState = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Submit for Review')) {
          return JSON.stringify({
            text: btns[i].textContent.trim(),
            disabled: btns[i].disabled,
            classes: btns[i].className.substring(0, 80),
            ariaDisabled: btns[i].getAttribute('aria-disabled')
          });
        }
      }
      return 'Not found';
    })()
  `);
  console.log('Submit button:', submitState);

  // Check for any validation errors on the page
  const errors = await c.ev(`
    (() => {
      var text = (document.querySelector('main') || document.body).innerText;
      var errorLines = [];
      var lines = text.split('\\n');
      for (var i = 0; i < lines.length; i++) {
        if (lines[i].toLowerCase().includes('error') || lines[i].toLowerCase().includes('required') || lines[i].toLowerCase().includes('please')) {
          errorLines.push(lines[i].trim());
        }
      }
      return JSON.stringify(errorLines);
    })()
  `);
  console.log('Errors:', errors);

  // Click Submit
  console.log('\n=== SUBMITTING ===');
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Submit for Review') && !btns[i].disabled) {
          btns[i].click();
          return 'Clicked';
        }
      }
      return 'Button not clickable';
    })()
  `);
  console.log(clicked);
  await sleep(10000);

  // Check result
  const url = await c.ev('window.location.href');
  console.log('\nURL:', url);
  const result = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
