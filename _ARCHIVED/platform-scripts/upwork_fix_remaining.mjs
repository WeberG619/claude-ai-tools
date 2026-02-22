// Fix title, rate, and skills using keyboard simulation
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

    // Select all text in focused input
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 }); // ctrl+a
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };

    // Type text character by character via CDP
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', {
          type: 'char',
          text: char,
          unmodifiedText: char
        });
        await sleep(20);
      }
    };

    // Press a special key
    const pressKey = async (key, code) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(50);
    };

    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, pressKey, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  const c = await connect(tab.webSocketDebuggerUrl);

  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(2000);
  console.log('On profile page\n');

  // ===== 1. FIX TITLE =====
  console.log('=== FIXING TITLE ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit title');
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  // Focus the title input
  const titleFocused = await c.ev(`
    (() => {
      const inputs = [...document.querySelectorAll('input[type="text"]')];
      // Find the title input (should contain current title)
      let input = inputs.find(i => i.value.includes('BIM Specialist') || i.value.includes('Revit'));
      if (!input) {
        // Try finding in modal
        const modal = document.querySelector('[role="dialog"], .air3-modal');
        if (modal) input = modal.querySelector('input[type="text"]');
      }
      if (!input && inputs.length) input = inputs[inputs.length - 1];
      if (input) {
        input.focus();
        input.select();
        return 'Focused: ' + input.value;
      }
      return 'No input found';
    })()
  `);
  console.log('Title input: ' + titleFocused);

  if (titleFocused.includes('Focused')) {
    // Select all and type new title
    await c.selectAll();
    await sleep(200);
    await c.typeText('Revit API Developer & BIM Automation Specialist | C# Plugins | AI Integration');
    await sleep(500);

    // Verify value
    const val = await c.ev(`document.activeElement?.value || 'no active element'`);
    console.log('New title value: ' + val);

    // Click save
    await sleep(300);
    await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' && b.offsetParent !== null
        );
        if (btn) btn.click();
        return btn ? 'saved' : 'no save btn';
      })()
    `);
    await sleep(2000);
    console.log('Title saved');
  }

  // ===== 2. FIX RATE =====
  console.log('\n=== FIXING RATE ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit hourly rate');
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  // Dump modal to understand rate UI
  const rateModal = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"], .air3-modal, [class*="modal"]');
      if (modal) return modal.innerText.substring(0, 1500);
      // Try finding rate input
      const inputs = [...document.querySelectorAll('input')].filter(i => i.offsetParent !== null);
      return 'Visible inputs: ' + inputs.map(i => i.type + '|' + i.name + '|' + i.value + '|' + i.placeholder).join(' | ');
    })()
  `);
  console.log('Rate modal:\n' + rateModal);

  // Focus rate input and clear + type
  const rateFocused = await c.ev(`
    (() => {
      const inputs = [...document.querySelectorAll('input')].filter(i => i.offsetParent !== null);
      // Find the rate input - should have value 50 or similar
      let input = inputs.find(i => i.value === '50' || i.value === '50.00' || i.value === '85');
      if (!input) input = inputs.find(i => i.type === 'text' || i.type === 'number');
      if (input) {
        input.focus();
        input.select();
        return 'Focused rate: ' + input.value + ' type=' + input.type;
      }
      return 'No rate input. Count: ' + inputs.length;
    })()
  `);
  console.log(rateFocused);

  if (rateFocused.includes('Focused')) {
    await c.selectAll();
    await sleep(200);
    await c.typeText('85');
    await sleep(500);

    const rateVal = await c.ev(`document.activeElement?.value || 'none'`);
    console.log('Rate value: ' + rateVal);

    // Save
    await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' && b.offsetParent !== null
        );
        if (btn) btn.click();
      })()
    `);
    await sleep(2000);
    console.log('Rate saved');
  }

  // ===== 3. ADD SKILLS =====
  console.log('\n=== ADDING SKILLS ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === 'Edit skills');
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  const skillsList = [
    'Autodesk Revit',
    'Revit API',
    'Building Information Modeling',
    'C#',
    'Python',
    'AutoCAD',
    'Architectural Drafting',
    'Construction Documents',
    'Plugin Development',
    '.NET Framework',
    'Dynamo',
    'Workflow Automation',
    'API Development',
    'Architecture'
  ];

  // Find skills search input
  const skillInput = await c.ev(`
    (() => {
      const inputs = [...document.querySelectorAll('input')].filter(i => i.offsetParent !== null);
      const search = inputs.find(i =>
        i.placeholder?.toLowerCase().includes('search') ||
        i.placeholder?.toLowerCase().includes('skill') ||
        i.getAttribute('aria-label')?.toLowerCase().includes('skill')
      );
      if (search) {
        search.focus();
        return 'Found skills input: ' + search.placeholder;
      }
      return 'Visible inputs: ' + inputs.map(i => i.placeholder + '|' + i.type).join('; ');
    })()
  `);
  console.log(skillInput);

  if (skillInput.includes('Found')) {
    for (const skill of skillsList) {
      console.log(`  Adding: ${skill}`);
      // Clear and type skill name
      await c.selectAll();
      await sleep(100);
      await c.typeText(skill);
      await sleep(1000);

      // Click the first suggestion dropdown item
      const selected = await c.ev(`
        (() => {
          const suggestions = document.querySelectorAll('[role="option"], [class*="suggestion"], [class*="dropdown"] li, [class*="listbox"] li, ul[role="listbox"] li');
          if (suggestions.length > 0) {
            suggestions[0].click();
            return 'Selected: ' + suggestions[0].textContent.trim().substring(0, 40);
          }
          // Try clicking any visible dropdown item
          const items = [...document.querySelectorAll('li, [role="menuitem"]')].filter(el =>
            el.offsetParent !== null &&
            el.textContent.toLowerCase().includes(skill.toLowerCase().substring(0, 5))
          );
          if (items.length) { items[0].click(); return 'Clicked matching item'; }
          return 'No suggestions found';
        })()
      `);
      console.log(`    ${selected}`);
      await sleep(500);
    }

    // Save skills
    await sleep(500);
    const skillsSaved = await c.ev(`
      (() => {
        const btn = [...document.querySelectorAll('button')].find(b =>
          b.textContent.trim().toLowerCase() === 'save' && b.offsetParent !== null
        );
        if (btn) { btn.click(); return 'Saved'; }
        return 'No save button';
      })()
    `);
    console.log('Skills save: ' + skillsSaved);
    await sleep(2000);
  }

  // ===== 4. ADD EMPLOYMENT =====
  console.log('\n=== ADDING EMPLOYMENT ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.getAttribute('aria-label') === 'Add employment history' ||
        b.textContent.trim() === 'Add employment'
      );
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  const empModal = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"], .air3-modal');
      if (modal) return modal.innerText.substring(0, 1500);
      return 'No modal';
    })()
  `);
  console.log('Employment modal:\n' + empModal);

  // ===== 5. FINAL CHECK =====
  console.log('\n\n=== RELOADING PROFILE ===');
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(3000);

  const title = await c.ev(`
    (() => {
      const h2s = [...document.querySelectorAll('h2, h3, [class*="title"]')];
      const profileTitle = h2s.find(h => h.textContent.includes('Specialist') || h.textContent.includes('Developer'));
      return profileTitle ? profileTitle.textContent.trim() : 'Title not found on page';
    })()
  `);
  console.log('Title: ' + title);

  const rate = await c.ev(`
    (() => {
      const el = [...document.querySelectorAll('*')].find(e => e.textContent.includes('/hr') && e.children.length === 0);
      return el ? el.textContent.trim() : 'Rate not found';
    })()
  `);
  console.log('Rate: ' + rate);

  const skills = await c.ev(`
    (() => {
      const section = [...document.querySelectorAll('section, div')].find(el =>
        el.textContent.includes('Skills') && el.textContent.includes('Self-reported')
      );
      return section ? section.innerText.substring(0, 500) : 'Skills section not found';
    })()
  `);
  console.log('Skills: ' + skills);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
