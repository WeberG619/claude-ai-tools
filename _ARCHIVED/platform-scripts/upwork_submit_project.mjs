// Set max projects and submit for review
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Check for simultaneous projects field
  console.log('=== SETTING MAX PROJECTS ===');
  const maxField = await c.ev(`
    (() => {
      // Look for number input or dropdown for max projects
      var inputs = document.querySelectorAll('input, select, [role="combobox"], [role="spinbutton"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].offsetParent && inputs[i].type !== 'search' && inputs[i].type !== 'hidden') {
          result.push({
            tag: inputs[i].tagName,
            type: inputs[i].type || '',
            id: inputs[i].id || '',
            value: inputs[i].value || '',
            role: inputs[i].getAttribute('role') || ''
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Fields:', maxField);

  // Try setting max projects (usually a dropdown or number input)
  const setMax = await c.ev(`
    (() => {
      // Look for number input
      var numInput = document.querySelector('input[type="number"]');
      if (numInput && numInput.offsetParent) {
        var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSet.call(numInput, '3');
        numInput.dispatchEvent(new Event('input', { bubbles: true }));
        numInput.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set number to 3';
      }

      // Look for select/dropdown
      var selects = document.querySelectorAll('select');
      for (var i = 0; i < selects.length; i++) {
        if (selects[i].offsetParent) {
          // Find option with value 3 or similar
          for (var j = 0; j < selects[i].options.length; j++) {
            if (selects[i].options[j].value === '3' || selects[i].options[j].text.includes('3')) {
              selects[i].value = selects[i].options[j].value;
              selects[i].dispatchEvent(new Event('change', { bubbles: true }));
              return 'Selected option: ' + selects[i].options[j].text;
            }
          }
          return 'Options: ' + Array.from(selects[i].options).map(o => o.text).join(', ');
        }
      }

      // Look for role="combobox"
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var k = 0; k < combos.length; k++) {
        if (combos[k].offsetParent) {
          combos[k].click();
          return 'Clicked combobox: ' + combos[k].textContent.trim().substring(0, 40);
        }
      }

      return 'No max projects field found';
    })()
  `);
  console.log('Max projects:', setMax);
  await sleep(1000);

  // If combobox was clicked, select an option
  if (setMax.includes('combobox')) {
    await sleep(500);
    const selectOpt = await c.ev(`
      (() => {
        var options = document.querySelectorAll('[role="option"]');
        for (var i = 0; i < options.length; i++) {
          if (options[i].offsetParent && (options[i].textContent.trim() === '3' || options[i].textContent.includes('3'))) {
            options[i].click();
            return 'Selected 3';
          }
        }
        // Just pick the first available option
        for (var j = 0; j < options.length; j++) {
          if (options[j].offsetParent) {
            return 'Available: ' + options[j].textContent.trim();
          }
        }
        return 'No options found';
      })()
    `);
    console.log('Selected:', selectOpt);
    await sleep(1000);
  }

  // Check the Terms checkbox
  console.log('\n=== ACCEPTING TERMS ===');
  const acceptTerms = await c.ev(`
    (() => {
      var checkboxes = document.querySelectorAll('input[type="checkbox"]');
      var results = [];
      for (var i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].offsetParent && !checkboxes[i].checked) {
          checkboxes[i].click();
          results.push('Checked: ' + (checkboxes[i].id || checkboxes[i].name || 'checkbox-' + i));
        }
      }
      return results.length > 0 ? results.join(', ') : 'No unchecked checkboxes (or already checked)';
    })()
  `);
  console.log(acceptTerms);
  await sleep(1000);

  // Check current state before submitting
  console.log('\n=== PRE-SUBMIT STATE ===');
  const preSubmit = await c.ev(`
    (() => {
      var text = (document.querySelector('main') || document.body).innerText;
      var submitBtn = null;
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim().includes('Submit for Review')) {
          submitBtn = { text: btns[i].textContent.trim(), disabled: btns[i].disabled };
        }
      }
      return JSON.stringify({ submitBtn, excerpt: text.substring(0, 500) });
    })()
  `);
  console.log(preSubmit);

  // Submit for review
  console.log('\n=== SUBMITTING FOR REVIEW ===');
  const submitted = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Submit for Review')) {
          btns[i].click();
          return 'Clicked Submit for Review';
        }
      }
      return 'Submit button not found';
    })()
  `);
  console.log(submitted);
  await sleep(8000);

  // Check result
  console.log('\n=== SUBMISSION RESULT ===');
  const url = await c.ev('window.location.href');
  console.log('URL:', url);
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log(resultText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
