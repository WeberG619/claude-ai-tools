// Debug: check what form fields are required on the proposal page
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

  // Get current URL
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  // Check for error messages
  console.log('\n=== ERROR MESSAGES ===');
  const errors = await c.ev(`
    (() => {
      var errorEls = document.querySelectorAll('[class*="error"], [class*="alert"], [class*="invalid"], [role="alert"], .text-danger, .text-error');
      var result = [];
      for (var i = 0; i < errorEls.length; i++) {
        if (errorEls[i].offsetParent && errorEls[i].textContent.trim().length > 0 && errorEls[i].textContent.trim().length < 200) {
          result.push({
            text: errorEls[i].textContent.trim(),
            tag: errorEls[i].tagName,
            classes: (typeof errorEls[i].className === 'string' ? errorEls[i].className : '').substring(0, 80)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(errors);

  // Get all form inputs
  console.log('\n=== ALL FORM INPUTS ===');
  const inputs = await c.ev(`
    (() => {
      var els = document.querySelectorAll('input, select, textarea, [role="combobox"], [role="listbox"], [role="spinbutton"]');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].offsetParent) {
          var label = '';
          var labelEl = els[i].closest('label') || document.querySelector('label[for="' + els[i].id + '"]');
          if (labelEl) label = labelEl.textContent.trim().substring(0, 60);
          // Also check parent section
          var parent = els[i].closest('section, fieldset, [class*="form-group"], [class*="field"]');
          var sectionText = parent ? parent.textContent.trim().substring(0, 100) : '';
          result.push({
            tag: els[i].tagName,
            type: els[i].type || '',
            id: els[i].id || '',
            name: els[i].name || '',
            value: (els[i].value || '').substring(0, 50),
            placeholder: (els[i].placeholder || '').substring(0, 50),
            required: els[i].required || false,
            label: label,
            section: sectionText.substring(0, 80),
            role: els[i].getAttribute('role') || ''
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(inputs);

  // Get the full form text
  console.log('\n=== FULL FORM TEXT ===');
  const formText = await c.ev(`(document.querySelector('main') || document.body).innerText`);
  console.log(formText.substring(0, 3000));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
