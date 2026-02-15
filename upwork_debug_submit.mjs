// Debug why Submit for Review isn't working
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
    const events = [];
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
      if (msg.method) {
        events.push(msg);
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, events, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Enable console and network monitoring
  await c.send('Console.enable');
  await c.send('Network.enable');
  await c.send('Runtime.enable');

  // 1. Check current URL and page state
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  // 2. Check for any dialogs/modals
  const modals = await c.ev(`
    (() => {
      var dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, [class*="modal"], [class*="dialog"], [class*="overlay"]');
      var result = [];
      for (var i = 0; i < dialogs.length; i++) {
        if (dialogs[i].offsetParent || window.getComputedStyle(dialogs[i]).display !== 'none') {
          result.push({
            tag: dialogs[i].tagName,
            role: dialogs[i].getAttribute('role') || '',
            classes: dialogs[i].className.substring(0, 80),
            text: dialogs[i].innerText.substring(0, 200)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\\n=== MODALS/DIALOGS ===');
  console.log(modals);

  // 3. Check for console errors
  const consoleErrors = await c.ev(`
    (() => {
      // Check if there are error toasts or notifications
      var toasts = document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="alert"], [class*="error"], [class*="snack"]');
      var result = [];
      for (var i = 0; i < toasts.length; i++) {
        if (toasts[i].offsetParent || window.getComputedStyle(toasts[i]).display !== 'none') {
          result.push({
            classes: toasts[i].className.substring(0, 80),
            text: toasts[i].innerText.substring(0, 200)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\\n=== TOASTS/ERRORS ===');
  console.log(consoleErrors);

  // 4. Check the submit button details more thoroughly
  const submitDetails = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var submitBtns = [];
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim();
        if (t.includes('Submit')) {
          var style = window.getComputedStyle(btns[i]);
          submitBtns.push({
            text: t,
            disabled: btns[i].disabled,
            ariaDisabled: btns[i].getAttribute('aria-disabled'),
            type: btns[i].type,
            form: btns[i].form ? btns[i].form.id : null,
            display: style.display,
            visibility: style.visibility,
            opacity: style.opacity,
            pointerEvents: style.pointerEvents,
            onclick: btns[i].onclick ? 'has onclick' : 'no onclick',
            parentForm: btns[i].closest('form') ? 'in form' : 'not in form',
            allAttrs: Array.from(btns[i].attributes).map(a => a.name + '=' + a.value.substring(0, 30)).join(', ')
          });
        }
      }
      return JSON.stringify(submitBtns, null, 2);
    })()
  `);
  console.log('\\n=== SUBMIT BUTTON DETAILS ===');
  console.log(submitDetails);

  // 5. Check ALL checkboxes and their states including hidden ones
  const allCheckboxes = await c.ev(`
    (() => {
      var cbs = document.querySelectorAll('input[type="checkbox"]');
      var result = [];
      for (var i = 0; i < cbs.length; i++) {
        var label = cbs[i].closest('label') || cbs[i].parentElement;
        result.push({
          checked: cbs[i].checked,
          disabled: cbs[i].disabled,
          visible: !!cbs[i].offsetParent,
          id: cbs[i].id || '',
          name: cbs[i].name || '',
          required: cbs[i].required,
          labelText: label ? label.textContent.trim().substring(0, 80) : ''
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\\n=== ALL CHECKBOXES ===');
  console.log(allCheckboxes);

  // 6. Check for any select/dropdown fields that might need values
  const selects = await c.ev(`
    (() => {
      var sels = document.querySelectorAll('select, [role="listbox"], [role="combobox"]');
      var result = [];
      for (var i = 0; i < sels.length; i++) {
        if (sels[i].offsetParent) {
          result.push({
            tag: sels[i].tagName,
            id: sels[i].id || '',
            value: sels[i].value || '',
            role: sels[i].getAttribute('role') || '',
            text: sels[i].textContent.trim().substring(0, 60)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\\n=== SELECTS/DROPDOWNS ===');
  console.log(selects);

  // 7. Check the max projects input specifically
  const maxProjects = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'hidden' && inputs[i].type !== 'checkbox' && inputs[i].type !== 'file') {
          result.push({
            type: inputs[i].type,
            id: inputs[i].id || '',
            value: inputs[i].value || '',
            name: inputs[i].name || '',
            placeholder: inputs[i].placeholder || '',
            min: inputs[i].min || '',
            max: inputs[i].max || ''
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('\\n=== VISIBLE INPUTS ===');
  console.log(maxProjects);

  // 8. Intercept network and try clicking submit
  console.log('\\n=== CLICKING SUBMIT (WITH NETWORK MONITORING) ===');

  // Set up fetch interceptor
  await c.ev(`
    window.__submitRequests = [];
    window.__origFetch = window.__origFetch || window.fetch;
    window.fetch = function() {
      var url = arguments[0];
      var opts = arguments[1] || {};
      if (typeof url === 'string') {
        window.__submitRequests.push({
          url: url.substring(0, 200),
          method: opts.method || 'GET',
          time: Date.now()
        });
      } else if (url && url.url) {
        window.__submitRequests.push({
          url: url.url.substring(0, 200),
          method: url.method || 'GET',
          time: Date.now()
        });
      }
      return window.__origFetch.apply(this, arguments);
    };
    'Interceptor set'
  `);

  // Also intercept XMLHttpRequest
  await c.ev(`
    window.__origXHROpen = window.__origXHROpen || XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
      window.__submitRequests.push({
        url: (url || '').substring(0, 200),
        method: method,
        type: 'xhr',
        time: Date.now()
      });
      return window.__origXHROpen.apply(this, arguments);
    };
    'XHR Interceptor set'
  `);

  // Now click submit
  const clicked = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Submit for Review') && !btns[i].disabled) {
          btns[i].click();
          return 'Clicked Submit';
        }
      }
      return 'Button not found or disabled';
    })()
  `);
  console.log('Click result:', clicked);

  // Wait and check network requests
  await sleep(5000);

  const requests = await c.ev(`JSON.stringify(window.__submitRequests || [])`);
  console.log('\\n=== NETWORK REQUESTS AFTER CLICK ===');
  console.log(requests);

  // Check for any new modals/dialogs
  const newModals = await c.ev(`
    (() => {
      var dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, [class*="modal"], [class*="dialog"]');
      var result = [];
      for (var i = 0; i < dialogs.length; i++) {
        var style = window.getComputedStyle(dialogs[i]);
        if (style.display !== 'none' && style.visibility !== 'hidden') {
          result.push({
            tag: dialogs[i].tagName,
            role: dialogs[i].getAttribute('role') || '',
            classes: dialogs[i].className.substring(0, 80),
            text: dialogs[i].innerText.substring(0, 500)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\\n=== POST-CLICK MODALS ===');
  console.log(newModals);

  // Check page text for any new messages
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log('\\n=== PAGE TEXT ===');
  console.log(pageText);

  // Check final URL
  const finalUrl = await c.ev('window.location.href');
  console.log('\\nFinal URL:', finalUrl);

  // Restore original fetch
  await c.ev(`
    if (window.__origFetch) window.fetch = window.__origFetch;
    if (window.__origXHROpen) XMLHttpRequest.prototype.open = window.__origXHROpen;
    'Restored'
  `);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
