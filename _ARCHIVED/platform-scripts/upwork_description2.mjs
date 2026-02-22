// Fix open forms, add steps and FAQs properly
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
    const pressTab = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
      await sleep(300);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, selectAll, pressTab, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // First, cancel any open forms
  console.log('=== CANCELING OPEN FORMS ===');
  const cancelResult = await c.ev(`
    (() => {
      var results = [];
      var btns = document.querySelectorAll('button');
      // Click all Cancel buttons (there might be multiple open forms)
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim() === 'Cancel') {
          btns[i].click();
          results.push('Cancelled');
        }
      }
      return results.length > 0 ? 'Cancelled ' + results.length + ' forms' : 'No forms to cancel';
    })()
  `);
  console.log(cancelResult);
  await sleep(2000);

  // Check current state
  console.log('\n=== CURRENT STATE ===');
  const state = await c.ev(`
    (() => {
      var main = document.querySelector('main') || document.body;
      var text = main.innerText;
      // Count existing steps
      var stepSection = text.includes('Check off steps');
      // Check for the "At least one step" error
      var hasStepError = text.includes('At least one step');
      // Count step items
      var stepItems = document.querySelectorAll('[class*="step-item"], [class*="step_item"]');
      return JSON.stringify({
        hasStepError,
        stepItems: stepItems.length,
        textExcerpt: text.substring(0, 1000)
      });
    })()
  `);
  console.log(state);

  // Now add steps properly
  console.log('\n=== ADDING STEPS ===');

  const steps = [
    { name: 'Requirements Review', desc: 'Review your needs and discuss plugin scope and Revit version' },
    { name: 'Architecture & Setup', desc: 'Design the solution and set up the Visual Studio project' },
    { name: 'Core Development', desc: 'Build the plugin functionality with regular progress updates' },
    { name: 'UI & Documentation', desc: 'Create the WPF interface, error handling, and documentation' },
    { name: 'Testing & Delivery', desc: 'Test in your Revit version and deliver the complete package' }
  ];

  for (const step of steps) {
    console.log('\nAdding step:', step.name);

    // Click "Add a step"
    const addClick = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a step') {
            btns[i].click();
            return 'Clicked';
          }
        }
        return 'Not found';
      })()
    `);
    console.log('Add step:', addClick);
    await sleep(1500);

    // Find the form fields - look for ALL visible inputs and textareas that aren't the description
    const formFields = await c.ev(`
      (() => {
        var allFields = document.querySelectorAll('input[type="text"], textarea');
        var fields = [];
        for (var i = 0; i < allFields.length; i++) {
          var el = allFields[i];
          if (el.offsetParent && el.id !== 'project-description' && el.type !== 'search') {
            fields.push({
              tag: el.tagName,
              id: el.id || '',
              placeholder: (el.placeholder || '').substring(0, 50),
              value: (el.value || '').substring(0, 50),
              isEmpty: el.value === ''
            });
          }
        }
        return JSON.stringify(fields);
      })()
    `);
    console.log('Fields:', formFields);

    const fields = JSON.parse(formFields);
    const emptyFields = fields.filter(f => f.isEmpty);

    if (emptyFields.length >= 2) {
      // First empty field = step name, second = step description
      // Focus first field (step name)
      await c.ev(`
        (() => {
          var allFields = document.querySelectorAll('input[type="text"], textarea');
          var empties = [];
          for (var i = 0; i < allFields.length; i++) {
            if (allFields[i].offsetParent && allFields[i].id !== 'project-description' && allFields[i].type !== 'search' && allFields[i].value === '') {
              empties.push(allFields[i]);
            }
          }
          if (empties.length >= 1) { empties[0].focus(); return 'Focused name'; }
          return 'No empty field';
        })()
      `);
      await sleep(200);
      await c.typeText(step.name);
      await sleep(300);

      // Tab to or focus second field (step description)
      await c.ev(`
        (() => {
          var allFields = document.querySelectorAll('input[type="text"], textarea');
          var empties = [];
          for (var i = 0; i < allFields.length; i++) {
            if (allFields[i].offsetParent && allFields[i].id !== 'project-description' && allFields[i].type !== 'search' && allFields[i].value === '') {
              empties.push(allFields[i]);
            }
          }
          if (empties.length >= 1) { empties[0].focus(); return 'Focused desc'; }
          return 'No empty desc field';
        })()
      `);
      await sleep(200);
      await c.typeText(step.desc);
      await sleep(300);
    } else if (emptyFields.length === 1) {
      // Single field
      await c.ev(`
        (() => {
          var allFields = document.querySelectorAll('input[type="text"], textarea');
          for (var i = 0; i < allFields.length; i++) {
            if (allFields[i].offsetParent && allFields[i].id !== 'project-description' && allFields[i].type !== 'search' && allFields[i].value === '') {
              allFields[i].focus();
              return 'Focused';
            }
          }
          return 'Not found';
        })()
      `);
      await sleep(200);
      await c.typeText(step.name);
      await sleep(300);
    }

    // Click Add
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
    console.log('Add result:', addResult);
    await sleep(1500);
  }

  // Add FAQs
  console.log('\n=== ADDING FAQs ===');

  const faqs = [
    {
      q: 'What Revit versions do you support?',
      a: 'I develop and test plugins for Revit 2024, 2025, and 2026.'
    },
    {
      q: 'Do I get the source code?',
      a: 'Yes, all tiers include the complete Visual Studio solution with source code and documentation.'
    }
  ];

  for (const faq of faqs) {
    console.log('\nAdding FAQ:', faq.q);

    const addQ = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim() === 'Add a question') {
            btns[i].click();
            return 'Clicked';
          }
        }
        return 'Not found';
      })()
    `);
    console.log('Add question:', addQ);
    await sleep(1500);

    // Find empty fields - question and answer
    const faqFields = await c.ev(`
      (() => {
        var allFields = document.querySelectorAll('input[type="text"], textarea');
        var empties = [];
        for (var i = 0; i < allFields.length; i++) {
          var el = allFields[i];
          if (el.offsetParent && el.id !== 'project-description' && el.type !== 'search' && el.value === '') {
            empties.push({
              tag: el.tagName,
              id: el.id || '',
              placeholder: (el.placeholder || '').substring(0, 50)
            });
          }
        }
        return JSON.stringify(empties);
      })()
    `);
    console.log('FAQ fields:', faqFields);

    const fFields = JSON.parse(faqFields);
    if (fFields.length >= 2) {
      // Question field
      await c.ev(`
        (() => {
          var allFields = document.querySelectorAll('input[type="text"], textarea');
          var empties = [];
          for (var i = 0; i < allFields.length; i++) {
            if (allFields[i].offsetParent && allFields[i].id !== 'project-description' && allFields[i].type !== 'search' && allFields[i].value === '') {
              empties.push(allFields[i]);
            }
          }
          if (empties[0]) { empties[0].focus(); return 'Focused Q'; }
        })()
      `);
      await sleep(200);
      await c.typeText(faq.q);
      await sleep(300);

      // Answer field
      await c.ev(`
        (() => {
          var allFields = document.querySelectorAll('input[type="text"], textarea');
          var empties = [];
          for (var i = 0; i < allFields.length; i++) {
            if (allFields[i].offsetParent && allFields[i].id !== 'project-description' && allFields[i].type !== 'search' && allFields[i].value === '') {
              empties.push(allFields[i]);
            }
          }
          if (empties[0]) { empties[0].focus(); return 'Focused A'; }
        })()
      `);
      await sleep(200);
      await c.typeText(faq.a);
      await sleep(300);

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
      console.log('Add FAQ result:', addFaq);
      await sleep(1500);
    }
  }

  // Final state
  console.log('\n=== FINAL DESCRIPTION STATE ===');
  const finalState = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(finalState);

  // Try Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  const cont = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & Continue')) {
          btns[i].click();
          return 'Clicked';
        }
      }
      return 'Not found';
    })()
  `);
  console.log(cont);
  await sleep(5000);

  // Check result
  const result = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log('\n=== RESULT ===');
  console.log(result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
