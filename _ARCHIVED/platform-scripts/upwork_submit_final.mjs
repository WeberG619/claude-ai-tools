// Set rate increase dropdowns and submit
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

  // We're on the apply page with errors
  console.log('=== STEP 1: SET FREQUENCY TO "Every 12 months" ===');

  // Click frequency dropdown
  await c.ev(`
    (() => {
      const dd = [...document.querySelectorAll('[role="combobox"]')]
        .find(d => d.textContent.trim().includes('Select a frequency') || d.textContent.trim().includes('Never'));
      if (dd) dd.click();
    })()
  `);
  await sleep(1000);

  // List and click "Every 12 months"
  const freqResult = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"]')].filter(o => o.offsetParent);
      const target = options.find(o => o.textContent.trim() === 'Every 12 months');
      if (target) { target.click(); return 'Selected: Every 12 months'; }
      return 'Options: ' + options.map(o => o.textContent.trim()).join(', ');
    })()
  `);
  console.log(freqResult);
  await sleep(1000);

  console.log('=== STEP 2: SET PERCENT TO 5% ===');
  // Click percent dropdown
  await c.ev(`
    (() => {
      const dd = [...document.querySelectorAll('[role="combobox"]')]
        .find(d => d.textContent.trim().includes('Select a percent') || d.textContent.trim().includes('%'));
      if (dd) { dd.click(); return 'clicked'; }
      // If "Select a percent" not found, list all dropdowns
      const all = [...document.querySelectorAll('[role="combobox"]')].filter(d => d.offsetParent);
      return 'Not found. Dropdowns: ' + all.map(d => d.textContent.trim().substring(0, 30)).join(' | ');
    })()
  `);
  await sleep(1000);

  const pctResult = await c.ev(`
    (() => {
      const options = [...document.querySelectorAll('[role="option"]')].filter(o => o.offsetParent);
      const target = options.find(o => o.textContent.trim().includes('5%'));
      if (target) { target.click(); return 'Selected: ' + target.textContent.trim(); }
      if (options.length > 0) {
        options[0].click();
        return 'Selected first: ' + options[0].textContent.trim();
      }
      return 'No options found';
    })()
  `);
  console.log(pctResult);
  await sleep(1000);

  // Verify dropdown state
  console.log('\n=== DROPDOWN STATE ===');
  const ddState = await c.ev(`
    (() => {
      const dds = [...document.querySelectorAll('[role="combobox"]')].filter(d => d.offsetParent);
      return dds.map(d => ({
        text: d.textContent.trim(),
        hasError: d.className.includes('error')
      }));
    })()
  `);
  console.log(JSON.stringify(ddState));

  // Check errors
  const errors = await c.ev(`
    (() => {
      return [...document.querySelectorAll('[class*="error"], [role="alert"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim());
    })()
  `);
  console.log('Errors:', JSON.stringify(errors));

  // Also verify cover letter is still there
  const letterOk = await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      return ta ? 'Letter length: ' + ta.value.length : 'no textarea';
    })()
  `);
  console.log(letterOk);

  // Submit
  console.log('\n=== SUBMITTING ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (btn && !btn.disabled) btn.click();
    })()
  `);
  await sleep(8000);

  // Check result
  const resultUrl = await c.ev('window.location.href');
  console.log('Result URL:', resultUrl);

  if (resultUrl.includes('apply')) {
    console.log('Still on apply page - checking remaining errors...');
    const remainingErrors = await c.ev(`
      (() => {
        return [...document.querySelectorAll('[class*="error"], [class*="alert-negative"]')]
          .filter(el => el.offsetParent && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim());
      })()
    `);
    console.log('Remaining errors:', JSON.stringify(remainingErrors));

    // Dump the full form state
    const formState = await c.ev(`
      (() => {
        const main = document.querySelector('main') || document.body;
        const inputs = [...main.querySelectorAll('input, textarea, select')]
          .filter(el => el.offsetParent)
          .map(el => ({
            tag: el.tagName, type: el.type, id: el.id,
            value: el.value?.substring(0, 60),
            placeholder: el.placeholder?.substring(0, 30)
          }));
        return JSON.stringify(inputs);
      })()
    `);
    console.log('Form state:', formState);
  } else {
    console.log('SUCCESS! Proposal submitted.');
    const successText = await c.ev(`document.body.innerText.substring(0, 500)`);
    console.log(successText);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
