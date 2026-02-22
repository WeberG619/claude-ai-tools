// Fix truncated title + properly add skills
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
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(20);
      }
    };
    const pressKey = async (key, code) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: key === 'Backspace' ? 8 : key === 'Enter' ? 13 : key === 'ArrowDown' ? 40 : 0 });
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

  // ===== SHORTER TITLE =====
  console.log('=== FIXING TITLE (shorter) ===');
  await c.ev(`document.querySelector('button[aria-label="Edit title"]')?.click()`);
  await sleep(2000);

  await c.ev(`
    (() => {
      const input = [...document.querySelectorAll('input[type="text"]')].find(i => i.value.includes('Revit') || i.value.includes('BIM'));
      if (input) { input.focus(); input.select(); }
    })()
  `);
  await sleep(300);
  await c.selectAll();
  await sleep(200);
  // "Revit BIM Specialist | C# Plugin Dev | AI Automation" = 53 chars
  await c.typeText('Revit BIM Specialist | C# Plugin Dev | AI Automation');
  await sleep(500);
  await c.ev(`[...document.querySelectorAll('button')].find(b => b.textContent.trim().toLowerCase() === 'save' && b.offsetParent)?.click()`);
  await sleep(2000);
  console.log('Title saved');

  // ===== SKILLS - proper approach =====
  console.log('\n=== ADDING SKILLS ===');
  await c.ev(`document.querySelector('button[aria-label="Edit skills"]')?.click()`);
  await sleep(2000);

  // First, let's understand the skills UI structure
  const skillsUI = await c.ev(`
    (() => {
      // Check for existing skill tokens/chips
      const tokens = [...document.querySelectorAll('[class*="token"], [class*="chip"], [class*="tag"], [class*="badge"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length < 50)
        .map(el => el.textContent.trim());

      // Find the search/input
      const inputs = [...document.querySelectorAll('input')]
        .filter(i => i.offsetParent)
        .map(i => ({ type: i.type, placeholder: i.placeholder, value: i.value, id: i.id, name: i.name, role: i.getAttribute('role'), ariaLabel: i.getAttribute('aria-label') }));

      // Check for a listbox
      const listbox = document.querySelector('[role="listbox"]');
      const combobox = document.querySelector('[role="combobox"]');

      return JSON.stringify({
        existingSkills: tokens.slice(0, 10),
        inputs,
        hasListbox: !!listbox,
        hasCombobox: !!combobox
      });
    })()
  `);
  console.log('Skills UI:', skillsUI);

  // Focus the skills search input
  await c.ev(`
    (() => {
      const input = [...document.querySelectorAll('input')].find(i =>
        i.offsetParent && (i.placeholder?.toLowerCase().includes('search') || i.getAttribute('role') === 'combobox')
      );
      if (input) input.focus();
    })()
  `);
  await sleep(300);

  const skillsToAdd = [
    'Autodesk Revit',
    'Building Information Modeling',
    'AutoCAD',
    'C#',
    'Python',
    'Architectural Drafting',
    'Construction Documents',
    '.NET Framework',
    'Architecture',
    'Revit Family Creation',
    'Workflow Automation',
    'API Development'
  ];

  for (const skill of skillsToAdd) {
    console.log(`\n  Trying: ${skill}`);

    // Clear input
    await c.selectAll();
    await sleep(100);

    // Type skill name
    await c.typeText(skill);
    await sleep(1500); // Wait for dropdown suggestions to appear

    // Check what suggestions appeared
    const suggestions = await c.ev(`
      (() => {
        // Look for suggestion items in dropdown
        const items = [...document.querySelectorAll('[role="option"], [role="listbox"] li, ul li, [class*="suggestion"], [class*="dropdown-item"], [class*="menu-item"]')]
          .filter(el => {
            if (!el.offsetParent) return false;
            const text = el.textContent.trim().toLowerCase();
            return text.length > 0 && text.length < 80;
          });
        return items.map(el => ({
          text: el.textContent.trim().substring(0, 60),
          role: el.getAttribute('role') || '',
          tag: el.tagName
        })).slice(0, 8);
      })()
    `);
    console.log('  Suggestions:', JSON.stringify(suggestions));

    if (suggestions.length > 0) {
      // Click the first matching suggestion
      const clicked = await c.ev(`
        (() => {
          const items = [...document.querySelectorAll('[role="option"], [role="listbox"] li, ul li, [class*="suggestion"], [class*="dropdown-item"]')]
            .filter(el => el.offsetParent && el.textContent.trim().length > 0 && el.textContent.trim().length < 80);
          if (items.length) {
            items[0].click();
            return 'Clicked: ' + items[0].textContent.trim();
          }
          return 'Nothing to click';
        })()
      `);
      console.log('  ' + clicked);
    } else {
      // Try pressing Enter to add the typed skill
      await c.pressKey('Enter', 'Enter');
      console.log('  Pressed Enter');
    }
    await sleep(500);

    // Re-focus input for next skill
    await c.ev(`
      (() => {
        const input = [...document.querySelectorAll('input')].find(i =>
          i.offsetParent && (i.placeholder?.toLowerCase().includes('search') || i.getAttribute('role') === 'combobox')
        );
        if (input) input.focus();
      })()
    `);
    await sleep(200);
  }

  // Save skills
  await sleep(500);
  const saved = await c.ev(`[...document.querySelectorAll('button')].find(b => b.textContent.trim().toLowerCase() === 'save' && b.offsetParent)?.click() || 'no save btn'`);
  console.log('\nSkills save clicked');
  await sleep(2000);

  // ===== VERIFY =====
  console.log('\n=== FINAL STATE ===');
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(3000);

  const finalTitle = await c.ev(`
    [...document.querySelectorAll('*')].find(el =>
      el.children.length === 0 && (el.textContent.includes('Specialist') || el.textContent.includes('Developer')) && el.textContent.includes('|')
    )?.textContent?.trim() || 'not found'
  `);
  console.log('Title: ' + finalTitle);

  const finalRate = await c.ev(`
    [...document.querySelectorAll('*')].find(el =>
      el.children.length === 0 && el.textContent.includes('/hr')
    )?.textContent?.trim() || 'not found'
  `);
  console.log('Rate: ' + finalRate);

  const finalSkills = await c.ev(`
    (() => {
      const heading = [...document.querySelectorAll('*')].find(el => el.textContent.trim() === 'Skills');
      if (heading) {
        const section = heading.closest('section') || heading.parentElement?.parentElement;
        if (section) return section.innerText.substring(0, 500);
      }
      return 'not found';
    })()
  `);
  console.log('Skills section: ' + finalSkills);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
