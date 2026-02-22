// Fill Description step and continue to Review
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function clickButton(c, text) {
  return await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('${text}')) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'Not found: ${text}';
    })()
  `);
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Step 1: Fill project description
  console.log('=== FILLING PROJECT DESCRIPTION ===');

  const description = `You'll get a custom-built Revit C# plugin tailored to your specific BIM workflow needs. I develop production-ready add-ins using the official Revit API, with clean code, custom WPF interfaces, and thorough documentation.

Every plugin comes as a complete Visual Studio solution with source code, a compiled DLL, an .addin manifest file, and an installation guide. I test in your target Revit version (2024, 2025, or 2026) and provide post-delivery support.

Whether you need automated data extraction, batch processing, custom ribbon tools, parameter management, or an AI-powered Revit assistant using named pipes IPC, I bring deep C#/.NET and Revit API expertise to deliver a polished, maintainable solution.`;

  // Focus and type into the textarea
  await c.ev(`document.getElementById('project-description')?.focus()`);
  await sleep(300);
  await c.typeText(description);
  await sleep(1000);

  // Verify character count
  const charCount = await c.ev(`document.getElementById('project-description')?.value?.length || 0`);
  console.log('Description length:', charCount, '(min 120, max 1200)');

  // Step 2: Add project steps
  console.log('\n=== ADDING PROJECT STEPS ===');

  const steps = [
    'Review your requirements and discuss the plugin scope, features, and target Revit version',
    'Design the plugin architecture, create the Visual Studio solution, and set up the Revit API project',
    'Develop the core functionality with regular progress updates and check-ins',
    'Build the WPF user interface, add error handling, and write documentation',
    'Test thoroughly in your target Revit version and deliver the complete solution package'
  ];

  for (const step of steps) {
    console.log('Adding step:', step.substring(0, 50) + '...');
    const addClick = await clickButton(c, 'Add a step');
    console.log(addClick);
    await sleep(1500);

    // Find the new textarea that appeared
    const typed = await c.ev(`
      (() => {
        // Look for the most recently added step textarea (usually the last visible one)
        var textareas = document.querySelectorAll('textarea');
        var stepTextarea = null;
        for (var i = textareas.length - 1; i >= 0; i--) {
          if (textareas[i].offsetParent && textareas[i].id !== 'project-description' && textareas[i].value === '') {
            stepTextarea = textareas[i];
            break;
          }
        }
        if (stepTextarea) {
          stepTextarea.focus();
          return 'Focused step textarea';
        }
        // Try input fields too
        var inputs = document.querySelectorAll('input[type="text"]');
        for (var j = inputs.length - 1; j >= 0; j--) {
          if (inputs[j].offsetParent && inputs[j].value === '' && inputs[j].type !== 'search') {
            inputs[j].focus();
            return 'Focused step input';
          }
        }
        return 'No empty textarea found';
      })()
    `);
    console.log(typed);

    if (typed.includes('Focused')) {
      await c.typeText(step);
      await sleep(500);

      // Try to save/confirm the step
      const saveStep = await c.ev(`
        (() => {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (btns[i].offsetParent && (t === 'save' || t === 'add' || t === 'done' || t === 'ok')) {
              btns[i].click();
              return 'Clicked: ' + btns[i].textContent.trim();
            }
          }
          return 'No save button (auto-saved?)';
        })()
      `);
      console.log('Save:', saveStep);
      await sleep(1000);
    }
  }

  // Step 3: Add FAQs
  console.log('\n=== ADDING FAQs ===');

  const faqs = [
    {
      q: 'What Revit versions do you support?',
      a: 'I develop and test plugins for Revit 2024, 2025, and 2026. If you need support for an older version, we can discuss feasibility during the requirements phase.'
    },
    {
      q: 'Do I get the source code?',
      a: 'Yes, all tiers include the complete Visual Studio solution with source code, compiled DLL, .addin manifest file, and installation documentation.'
    },
    {
      q: 'How do revisions work?',
      a: 'Each tier includes a set number of revisions. A revision covers changes to existing functionality within the original scope. New features or scope changes may require a separate agreement.'
    }
  ];

  for (const faq of faqs) {
    console.log('Adding FAQ:', faq.q.substring(0, 40) + '...');
    const addQ = await clickButton(c, 'Add a question');
    console.log(addQ);
    await sleep(2000);

    // Check what appeared (might be a modal or inline form)
    const faqForm = await c.ev(`
      (() => {
        var modal = document.querySelector('[role="dialog"]');
        var scope = modal || document;
        var textareas = scope.querySelectorAll('textarea');
        var inputs = scope.querySelectorAll('input[type="text"]');
        var visible = [];
        for (var i = 0; i < textareas.length; i++) {
          if (textareas[i].offsetParent && textareas[i].value === '') {
            visible.push({ tag: 'TEXTAREA', id: textareas[i].id, placeholder: textareas[i].placeholder?.substring(0, 40) || '' });
          }
        }
        for (var j = 0; j < inputs.length; j++) {
          if (inputs[j].offsetParent && inputs[j].value === '' && inputs[j].type !== 'search') {
            visible.push({ tag: 'INPUT', id: inputs[j].id, placeholder: inputs[j].placeholder?.substring(0, 40) || '' });
          }
        }
        return JSON.stringify({ hasModal: !!modal, fields: visible });
      })()
    `);
    console.log('FAQ form:', faqForm);

    const parsed = JSON.parse(faqForm);
    if (parsed.fields.length >= 2) {
      // First field = question, second = answer
      const qField = parsed.fields[0];
      const aField = parsed.fields[1];

      // Type question
      await c.ev(`
        (() => {
          var el = document.getElementById('${qField.id}') || document.querySelectorAll('${qField.tag.toLowerCase()}')[0];
          if (el) el.focus();
        })()
      `);
      await sleep(200);
      await c.typeText(faq.q);
      await sleep(300);

      // Type answer
      await c.ev(`
        (() => {
          var fields = document.querySelectorAll('textarea, input[type="text"]');
          for (var i = 0; i < fields.length; i++) {
            if (fields[i].offsetParent && fields[i].value === '' && fields[i].type !== 'search') {
              fields[i].focus();
              return 'Focused answer field';
            }
          }
          return 'No empty answer field found';
        })()
      `);
      await sleep(200);
      await c.typeText(faq.a);
      await sleep(300);

      // Save FAQ
      const saveFaq = await c.ev(`
        (() => {
          var modal = document.querySelector('[role="dialog"]');
          var scope = modal || document;
          var btns = scope.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (btns[i].offsetParent && (t === 'save' || t === 'add' || t === 'done')) {
              btns[i].click();
              return 'Clicked: ' + btns[i].textContent.trim();
            }
          }
          return 'No save button';
        })()
      `);
      console.log('Save FAQ:', saveFaq);
      await sleep(2000);
    } else if (parsed.fields.length === 1) {
      // Single field - just type question, answer might come after
      await c.ev(`
        (() => {
          var el = document.getElementById('${parsed.fields[0].id}');
          if (!el) {
            var fields = document.querySelectorAll('textarea, input[type="text"]');
            for (var i = 0; i < fields.length; i++) {
              if (fields[i].offsetParent && fields[i].value === '' && fields[i].type !== 'search') {
                el = fields[i];
                break;
              }
            }
          }
          if (el) el.focus();
        })()
      `);
      await sleep(200);
      await c.typeText(faq.q);
      await sleep(500);
    }
  }

  // Check final state before continuing
  console.log('\n=== DESCRIPTION STATE ===');
  const state = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(state);

  // Click Save & Continue
  console.log('\n=== SAVE & CONTINUE ===');
  const cont = await clickButton(c, 'Save & Continue');
  console.log(cont);
  await sleep(5000);

  // Step 6: Review
  console.log('\n=== STEP 6: REVIEW ===');
  const step6 = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 4000)`);
  console.log(step6);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
