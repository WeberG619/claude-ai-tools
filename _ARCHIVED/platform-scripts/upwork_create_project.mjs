// Navigate to project dashboard and create project offerings
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
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Go to project dashboard
  console.log('=== PROJECT DASHBOARD ===');
  await c.nav('https://www.upwork.com/nx/project-dashboard/');
  await sleep(3000);

  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  const pageText = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 3000)');
  console.log(pageText);

  // Look for "Create" or "Add" buttons
  console.log('\n=== BUTTONS ===');
  const buttons = await c.ev(`
    (() => {
      const btns = [...document.querySelectorAll('button, a')]
        .filter(el => el.offsetParent)
        .filter(el => {
          const t = el.textContent.trim().toLowerCase();
          return t.includes('create') || t.includes('add') || t.includes('new') || t.includes('start');
        })
        .map(el => ({ tag: el.tagName, text: el.textContent.trim().substring(0, 60), href: el.href || '' }));
      return JSON.stringify(btns);
    })()
  `);
  console.log(buttons);

  // Click "Create a project" or similar
  console.log('\n=== CLICKING CREATE ===');
  const createClicked = await c.ev(`
    (() => {
      const btns = [...document.querySelectorAll('button, a')].filter(el => el.offsetParent);
      const create = btns.find(el => {
        const t = el.textContent.trim().toLowerCase();
        return t.includes('create') && t.includes('project');
      }) || btns.find(el => {
        const t = el.textContent.trim().toLowerCase();
        return t.includes('create') || (t.includes('add') && t.includes('project'));
      });
      if (create) {
        create.click();
        return 'Clicked: ' + create.textContent.trim() + ' | href: ' + (create.href || 'none');
      }
      return 'No create button found';
    })()
  `);
  console.log(createClicked);
  await sleep(5000);

  // Check what appeared
  url = await c.ev('window.location.href');
  console.log('\nNew URL:', url);
  const newPage = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 3000)');
  console.log(newPage);

  // Get all form elements
  console.log('\n=== FORM ELEMENTS ===');
  const formElements = await c.ev(`
    (() => {
      const inputs = [...document.querySelectorAll('input, textarea, select')]
        .filter(el => el.offsetParent)
        .map(el => ({
          tag: el.tagName,
          type: el.type || '',
          name: el.name || '',
          placeholder: el.placeholder || '',
          id: el.id || '',
          label: el.closest('label')?.textContent?.trim()?.substring(0, 60) || '',
          ariaLabel: el.getAttribute('aria-label') || ''
        }));
      const dropdowns = [...document.querySelectorAll('[role="combobox"]')]
        .filter(d => d.offsetParent)
        .map(d => ({
          text: d.textContent.trim().substring(0, 60),
          ariaLabelledBy: d.getAttribute('aria-labelledby')
        }));
      return JSON.stringify({ inputs, dropdowns });
    })()
  `);
  console.log(formElements);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
