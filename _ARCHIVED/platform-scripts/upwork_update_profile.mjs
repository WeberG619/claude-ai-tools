// Update Upwork profile fields via CDP - click edit buttons, fill modals, save
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
    // Type text via CDP Input.dispatchKeyEvent
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'keyDown', text: char });
        await send('Input.dispatchKeyEvent', { type: 'keyUp', text: char });
        await sleep(15);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  const c = await connect(tab.webSocketDebuggerUrl);

  // Navigate to profile page
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(2000);
  console.log('On profile page\n');

  // ===== 1. EDIT TITLE =====
  console.log('=== EDITING TITLE ===');
  const titleClicked = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit title');
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    })()
  `);
  console.log('Edit title button: ' + titleClicked);
  await sleep(2000);

  if (titleClicked === 'clicked') {
    // Find the title input in the modal
    const titleSet = await c.ev(`
      (() => {
        // Look for input or textarea in modal/dialog
        const inputs = [...document.querySelectorAll('input[type="text"], textarea')];
        const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
        let input = null;
        if (modal) {
          input = modal.querySelector('input[type="text"], textarea');
        }
        if (!input && inputs.length > 0) {
          // Find the one that has the current title value
          input = inputs.find(i => i.value.includes('BIM Specialist') || i.value.includes('Technical Writer'));
          if (!input) input = inputs[inputs.length - 1]; // last input
        }
        if (input) {
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set ||
                                          Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
          if (nativeInputValueSetter) {
            nativeInputValueSetter.call(input, 'Revit API Developer & BIM Automation Specialist | C# Plugins | AI Integration');
          } else {
            input.value = 'Revit API Developer & BIM Automation Specialist | C# Plugins | AI Integration';
          }
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Title set to: ' + input.value;
        }
        return 'No input found in modal. Modal exists: ' + !!modal;
      })()
    `);
    console.log(titleSet);

    // Click Save
    await sleep(500);
    const titleSaved = await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' ||
          b.textContent.trim().toLowerCase() === 'save profile'
        );
        if (btn) { btn.click(); return 'Saved'; }
        return 'No save button found';
      })()
    `);
    console.log('Save: ' + titleSaved);
    await sleep(2000);
  }

  // ===== 2. EDIT HOURLY RATE =====
  console.log('\n=== EDITING HOURLY RATE ===');
  const rateClicked = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit hourly rate');
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    })()
  `);
  console.log('Edit rate button: ' + rateClicked);
  await sleep(2000);

  if (rateClicked === 'clicked') {
    const rateSet = await c.ev(`
      (() => {
        const inputs = [...document.querySelectorAll('input')];
        const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
        let input = null;
        if (modal) {
          input = modal.querySelector('input[type="text"], input[type="number"], input:not([type="hidden"])');
        }
        if (!input) input = inputs.find(i => i.value === '50' || i.value === '50.00');
        if (input) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
          if (setter) setter.call(input, '85');
          else input.value = '85';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Rate set to: ' + input.value;
        }
        // Dump all visible inputs for debugging
        return 'Inputs: ' + inputs.map(i => i.type + '=' + i.value).join(', ');
      })()
    `);
    console.log(rateSet);

    await sleep(500);
    const rateSaved = await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' && b.offsetParent !== null
        );
        if (btn) { btn.click(); return 'Saved'; }
        return 'No save button';
      })()
    `);
    console.log('Save: ' + rateSaved);
    await sleep(2000);
  }

  // ===== 3. EDIT DESCRIPTION/BIO =====
  console.log('\n=== EDITING DESCRIPTION ===');
  const descClicked = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit description');
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    })()
  `);
  console.log('Edit description button: ' + descClicked);
  await sleep(2000);

  if (descClicked === 'clicked') {
    const newBio = `I build custom Revit plugins, automate BIM workflows, and integrate AI into architectural production pipelines. I don't do manual drafting — I build the tools that make drafting faster.

What I do:
• Custom Revit API plugins (C#/.NET) — add-ins, automation tools, data extraction, batch processing
• BIM workflow automation — Dynamo scripts, Python automation, batch operations across models
• AI + Revit integration — I built RevitMCPBridge, an open-source bridge connecting AI assistants directly to Revit for automated model operations
• Revit template and family development — standards, shared parameters, project templates
• Data extraction and reporting — schedule exports, model auditing, QA/QC automation

Background: I work daily in Revit 2025/2026 on commercial architecture, medical facilities, and retail projects. I understand production workflows because I run them — which means the tools I build solve real problems, not theoretical ones.

Tech stack: C#, .NET, Revit API, Python, Dynamo, WPF/XAML, AI/LLM integration, named pipes IPC, Git.`;

    const bioSet = await c.ev(`
      (() => {
        const textareas = [...document.querySelectorAll('textarea')];
        const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
        let textarea = null;
        if (modal) textarea = modal.querySelector('textarea');
        if (!textarea) textarea = textareas.find(t => t.value.includes('BIM specialist') || t.value.includes('writing'));
        if (!textarea && textareas.length) textarea = textareas[textareas.length - 1];
        if (textarea) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
          const bio = ${JSON.stringify(newBio)};
          if (setter) setter.call(textarea, bio);
          else textarea.value = bio;
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
          textarea.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Bio set, length: ' + textarea.value.length;
        }
        return 'No textarea found. Modal: ' + !!modal;
      })()
    `);
    console.log(bioSet);

    await sleep(500);
    const bioSaved = await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' && b.offsetParent !== null
        );
        if (btn) { btn.click(); return 'Saved'; }
        return 'No save button';
      })()
    `);
    console.log('Save: ' + bioSaved);
    await sleep(2000);
  }

  // ===== 4. EDIT SKILLS =====
  console.log('\n=== EDITING SKILLS ===');
  const skillsClicked = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit skills');
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    })()
  `);
  console.log('Edit skills button: ' + skillsClicked);
  await sleep(2000);

  if (skillsClicked === 'clicked') {
    // Dump the skills modal content to understand the UI
    const skillsModal = await c.ev(`
      (() => {
        const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
        if (modal) return modal.innerText.substring(0, 2000);
        // Maybe it's inline
        return document.body.innerText.substring(0, 3000);
      })()
    `);
    console.log('Skills modal content:\n' + skillsModal);

    // Find the skills input and try adding skills
    const skillsAdded = await c.ev(`
      (() => {
        const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
        const container = modal || document;
        const input = container.querySelector('input[type="text"], input[type="search"], input[placeholder*="skill"], input[placeholder*="search"]');
        if (input) return 'Found skills input: placeholder=' + input.placeholder + ' value=' + input.value;
        const inputs = [...container.querySelectorAll('input')];
        return 'Inputs found: ' + inputs.map(i => i.type + '|' + i.placeholder + '|' + i.value).join('; ');
      })()
    `);
    console.log(skillsAdded);
  }

  // ===== 5. CHECK FINAL STATE =====
  console.log('\n\n=== FINAL PROFILE STATE ===');
  // Close any modal first
  await c.ev(`
    (() => {
      const closeBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.includes('Cancel') || b.getAttribute('aria-label')?.includes('Close') || b.getAttribute('aria-label')?.includes('close')
      );
      if (closeBtn) closeBtn.click();
    })()
  `);
  await sleep(1000);

  // Reload profile
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(3000);
  const finalState = await c.ev('document.body.innerText.substring(0, 4000)');
  console.log(finalState);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
