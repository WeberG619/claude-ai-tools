// Edit Upwork profile - navigate to profile page and find edit controls
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  const c = await connect(tab.webSocketDebuggerUrl);

  // 1. Go to the actual profile page
  console.log('=== PROFILE PAGE ===');
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(2000);
  let url = await c.ev('location.href');
  let text = await c.ev('document.body.innerText.substring(0, 6000)');
  console.log('URL:', url);
  console.log(text);

  // 2. Find all edit/pencil buttons on the profile page
  console.log('\n=== EDIT BUTTONS ON PROFILE ===');
  let editBtns = await c.ev(`
    JSON.stringify(
      [...document.querySelectorAll('button, a, [role="button"], [data-cy], [data-qa], [class*="edit"], [class*="Edit"], [aria-label*="edit"], [aria-label*="Edit"]')]
        .filter(el => {
          const t = (el.textContent||'').toLowerCase();
          const a = (el.getAttribute('aria-label')||'').toLowerCase();
          const cl = (el.className||'').toLowerCase();
          return t.includes('edit') || a.includes('edit') || cl.includes('edit') ||
                 t.includes('add') || a.includes('add') ||
                 cl.includes('pencil') || a.includes('pencil');
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          ariaLabel: el.getAttribute('aria-label') || '',
          href: el.href || '',
          className: (el.className||'').substring(0, 80),
          dataCy: el.getAttribute('data-cy') || '',
          dataQa: el.getAttribute('data-qa') || ''
        }))
        .slice(0, 30)
    )
  `);
  console.log(editBtns);

  // 3. Also check for SVG icons (pencil icons used as edit buttons)
  console.log('\n=== SVG/ICON EDIT BUTTONS ===');
  let svgBtns = await c.ev(`
    JSON.stringify(
      [...document.querySelectorAll('button, [role="button"]')]
        .filter(el => el.querySelector('svg') || el.querySelector('[class*="icon"]'))
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          ariaLabel: el.getAttribute('aria-label') || '',
          parentText: el.parentElement?.textContent?.trim()?.substring(0, 60) || '',
          className: (el.className||'').substring(0, 80)
        }))
        .slice(0, 20)
    )
  `);
  console.log(svgBtns);

  // 4. Try the specialized profile creation page - this might have the full form
  console.log('\n\n=== SPECIALIZED PROFILE CREATION ===');
  await c.nav('https://www.upwork.com/freelancers/create-service-profile');
  await sleep(3000);
  text = await c.ev('document.body.innerText.substring(0, 5000)');
  console.log(text);

  // 5. Also check settings for experience level radios and try to set Expert
  console.log('\n\n=== SET EXPERIENCE LEVEL ===');
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(2000);

  // Click Expert radio (value "3")
  const expertSet = await c.ev(`
    (() => {
      const radio = document.querySelector('input[name="radio-group-3"]') ||
                     document.querySelector('input[value="3"]') ||
                     [...document.querySelectorAll('input[type="radio"]')][2];
      if (radio) {
        radio.click();
        radio.checked = true;
        radio.dispatchEvent(new Event('change', {bubbles: true}));
        radio.dispatchEvent(new Event('input', {bubbles: true}));
        return 'Expert radio clicked';
      }
      return 'Radio not found';
    })()
  `);
  console.log(expertSet);
  await sleep(1000);

  // Check if there's a save button
  const saveBtn = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')]
        .find(b => b.textContent.toLowerCase().includes('save'));
      if (btn) { return 'Save button found: ' + btn.textContent.trim(); }
      return 'No save button visible';
    })()
  `);
  console.log(saveBtn);

  // Dump the full page HTML structure around the radio buttons
  console.log('\n=== RADIO BUTTON CONTEXT ===');
  const radioContext = await c.ev(`
    (() => {
      const radios = [...document.querySelectorAll('input[type="radio"]')];
      return radios.map(r => {
        const section = r.closest('section, div[class*="card"], div[class*="section"]');
        return {
          name: r.name,
          value: r.value,
          checked: r.checked,
          sectionText: section ? section.textContent.trim().substring(0, 200) : 'no parent section'
        };
      });
    })()
  `);
  console.log(JSON.stringify(radioContext, null, 2));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
