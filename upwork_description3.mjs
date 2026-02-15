// Debug and fix step/FAQ forms
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
        await sleep(6);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Cancel any open forms
  console.log('=== CANCELING FORMS ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Cancel') btns[i].click();
      }
    })()
  `);
  await sleep(1000);
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Cancel') btns[i].click();
      }
    })()
  `);
  await sleep(1000);

  // Debug: Click "Add a step" and inspect ALL form elements
  console.log('\n=== DEBUG: ADD A STEP FORM ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a step') {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(2000);

  // Find ALL visible form-like elements
  const allElements = await c.ev(`
    (() => {
      var els = document.querySelectorAll('input, textarea, select, [contenteditable]');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].offsetParent && els[i].type !== 'hidden') {
          result.push({
            tag: els[i].tagName,
            type: els[i].type || '',
            id: els[i].id || '',
            name: els[i].name || '',
            placeholder: (els[i].placeholder || '').substring(0, 50),
            value: (els[i].value || '').substring(0, 50),
            classes: els[i].className.substring(0, 60),
            ariaLabel: (els[i].getAttribute('aria-label') || '').substring(0, 50)
          });
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('All form elements:');
  console.log(allElements);

  // Cancel the step form
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Cancel') { btns[i].click(); return; }
      }
    })()
  `);
  await sleep(1000);

  // Now add steps using the correct selectors
  console.log('\n=== ADDING STEPS ===');
  const steps = [
    { name: 'Requirements Review', desc: 'Review your needs, scope, and Revit version' },
    { name: 'Architecture & Setup', desc: 'Design the solution and create the VS project' },
    { name: 'Core Development', desc: 'Build plugin functionality with progress updates' },
    { name: 'UI & Testing', desc: 'Create WPF interface and test in target Revit' },
    { name: 'Delivery', desc: 'Deliver complete package with documentation' }
  ];

  for (const step of steps) {
    console.log('\nStep:', step.name);

    // Click Add a step
    await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a step') {
            btns[i].click();
            return 'Clicked';
          }
        }
      })()
    `);
    await sleep(1500);

    // Focus the step name input (look for input with id containing 'name' or type=text near the step section)
    const focusName = await c.ev(`
      (() => {
        // Try by id pattern
        var nameInput = document.getElementById('input-step-name') || document.querySelector('input[id*="step"][id*="name"]');
        if (!nameInput) {
          // Try by placeholder
          var inputs = document.querySelectorAll('input');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent && inputs[i].type !== 'search' && inputs[i].type !== 'hidden' &&
                inputs[i].type !== 'checkbox' && inputs[i].type !== 'radio' &&
                (inputs[i].placeholder.toLowerCase().includes('step') || inputs[i].placeholder.toLowerCase().includes('name') || inputs[i].value === '')) {
              nameInput = inputs[i];
              break;
            }
          }
        }
        if (!nameInput) {
          // Try ALL inputs that are not search
          var inputs2 = document.querySelectorAll('input');
          for (var j = 0; j < inputs2.length; j++) {
            if (inputs2[j].offsetParent && inputs2[j].type !== 'search' && inputs2[j].type !== 'hidden' &&
                inputs2[j].type !== 'checkbox' && inputs2[j].type !== 'radio' && inputs2[j].type !== 'file') {
              nameInput = inputs2[j];
              break;
            }
          }
        }
        if (nameInput) {
          nameInput.focus();
          return 'Focused name: type=' + nameInput.type + ' id=' + nameInput.id + ' placeholder=' + nameInput.placeholder;
        }
        return 'No name input found';
      })()
    `);
    console.log(focusName);

    if (focusName.includes('Focused')) {
      await c.selectAll();
      await sleep(100);
      await c.typeText(step.name);
      await sleep(300);
    }

    // Now focus the description textarea
    const focusDesc = await c.ev(`
      (() => {
        var ta = document.getElementById('textarea-detail');
        if (!ta) {
          var textareas = document.querySelectorAll('textarea');
          for (var i = 0; i < textareas.length; i++) {
            if (textareas[i].offsetParent && textareas[i].id !== 'project-description') {
              ta = textareas[i];
              break;
            }
          }
        }
        if (ta) {
          ta.focus();
          return 'Focused desc: id=' + ta.id;
        }
        return 'No desc textarea found';
      })()
    `);
    console.log(focusDesc);

    if (focusDesc.includes('Focused')) {
      await c.selectAll();
      await sleep(100);
      await c.typeText(step.desc);
      await sleep(300);
    }

    // Click Add button
    const addResult = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add') {
            btns[i].click();
            return 'Added';
          }
        }
        return 'No Add button';
      })()
    `);
    console.log('Result:', addResult);
    await sleep(1500);
  }

  // Add FAQs
  console.log('\n=== ADDING FAQs ===');

  // First debug FAQ form
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a question') {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(1500);

  const faqDebug = await c.ev(`
    (() => {
      var els = document.querySelectorAll('input, textarea');
      var result = [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].offsetParent && els[i].type !== 'search' && els[i].type !== 'hidden' &&
            els[i].type !== 'checkbox' && els[i].type !== 'file' && els[i].id !== 'project-description') {
          result.push({
            tag: els[i].tagName, type: els[i].type, id: els[i].id,
            placeholder: els[i].placeholder?.substring(0, 40), value: els[i].value?.substring(0, 20)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('FAQ form elements:', faqDebug);

  // Cancel and re-add properly
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Cancel') { btns[i].click(); return; }
      }
    })()
  `);
  await sleep(1000);

  const faqs = [
    { q: 'What Revit versions do you support?', a: 'I build and test for Revit 2024, 2025, and 2026.' },
    { q: 'Do I get the source code?', a: 'Yes, all tiers include the full VS solution with source code and docs.' }
  ];

  for (const faq of faqs) {
    console.log('\nFAQ:', faq.q);

    await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a question') {
            btns[i].click();
            return 'Clicked';
          }
        }
      })()
    `);
    await sleep(1500);

    // Focus question field (first non-search, non-desc input/textarea that's empty)
    const focusQ = await c.ev(`
      (() => {
        var els = document.querySelectorAll('input, textarea');
        for (var i = 0; i < els.length; i++) {
          if (els[i].offsetParent && els[i].type !== 'search' && els[i].type !== 'hidden' &&
              els[i].type !== 'checkbox' && els[i].type !== 'file' && els[i].id !== 'project-description' &&
              els[i].id !== 'textarea-detail' && els[i].value === '') {
            els[i].focus();
            return 'Focused Q: tag=' + els[i].tagName + ' id=' + els[i].id + ' placeholder=' + els[i].placeholder;
          }
        }
        return 'No Q field';
      })()
    `);
    console.log(focusQ);

    if (focusQ.includes('Focused')) {
      await c.typeText(faq.q);
      await sleep(300);
    }

    // Focus answer field
    const focusA = await c.ev(`
      (() => {
        var els = document.querySelectorAll('input, textarea');
        for (var i = 0; i < els.length; i++) {
          if (els[i].offsetParent && els[i].type !== 'search' && els[i].type !== 'hidden' &&
              els[i].type !== 'checkbox' && els[i].type !== 'file' && els[i].id !== 'project-description' &&
              els[i].value === '') {
            els[i].focus();
            return 'Focused A: tag=' + els[i].tagName + ' id=' + els[i].id;
          }
        }
        return 'No A field';
      })()
    `);
    console.log(focusA);

    if (focusA.includes('Focused')) {
      await c.typeText(faq.a);
      await sleep(300);
    }

    // Click Add
    const addFaq = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add') {
            btns[i].click();
            return 'Added';
          }
        }
        return 'No Add button';
      })()
    `);
    console.log('Result:', addFaq);
    await sleep(1500);
  }

  // Final state
  console.log('\n=== FINAL STATE ===');
  const finalText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(finalText);

  // Try Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked';
        }
      }
    })()
  `);
  await sleep(5000);

  const result = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
