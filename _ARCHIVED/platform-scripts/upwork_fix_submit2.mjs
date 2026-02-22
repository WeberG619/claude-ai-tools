// Fresh approach - reload proposal page and fill correctly
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
        await sleep(8);
      }
    };
    const pressTab = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
      await sleep(200);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, pressTab, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Reload the proposal page fresh
  console.log('=== RELOADING PROPOSAL PAGE ===');
  await c.nav('https://www.upwork.com/nx/proposals/job/~022021630179255436296/apply/');
  await sleep(5000);

  // Check the default rate
  const defaultRate = await c.ev(`document.getElementById('step-rate')?.value`);
  console.log('Default rate:', defaultRate);

  // The rate should already be $85.00 from the profile
  // If it's already correct, skip changing it
  if (defaultRate === '$85.00') {
    console.log('Rate is already correct at $85.00');
  } else {
    // Clear and set rate using triple-click + keyboard
    console.log('Fixing rate...');
    await c.ev(`
      (() => {
        const input = document.getElementById('step-rate');
        if (input) {
          input.focus();
          // Use triple-click simulation by dispatching click events
          input.setSelectionRange(0, input.value.length);
        }
      })()
    `);
    await sleep(200);
    // Delete everything
    for (let i = 0; i < 15; i++) {
      await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
      await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
      await sleep(30);
    }
    await sleep(200);
    await c.typeText('85');
    await sleep(500);
    await c.pressTab();
    await sleep(1000);
  }

  const rateCheck = await c.ev(`
    JSON.stringify({
      rate: document.getElementById('step-rate')?.value,
      fee: document.getElementById('fee-rate')?.value,
      receive: document.getElementById('receive-step-rate')?.value
    })
  `);
  console.log('Rates:', rateCheck);

  // Write cover letter
  console.log('\n=== COVER LETTER ===');
  await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      if (ta) ta.focus();
    })()
  `);
  await sleep(300);

  const coverLetter = [
    'I build Revit add-ins daily and this is a straightforward project I can deliver quickly.',
    '',
    'Relevant experience:',
    '- I develop C# Revit API plugins professionally, working in Revit 2025/2026 every day',
    '- I built RevitMCPBridge (open-source on GitHub) - a full IPC bridge between AI assistants and Revit using named pipes and the Revit API',
    '- Experienced with adaptive components, placement APIs, and element selection workflows',
    '',
    'For your add-in, I would implement:',
    '- A ribbon button that triggers a selection workflow (PickObject for each adaptive point)',
    '- Placement of the 2-point adaptive family using AdaptiveComponentInstanceUtils',
    '- Proper adaptive point assignment so the profile follows when points move',
    '',
    'I can have a working prototype within 2-3 days, with the complete Visual Studio solution, compiled DLL, .addin file, and documentation.',
    '',
    'Happy to discuss approach or answer questions before starting.'
  ].join('\n');

  await c.typeText(coverLetter);
  await sleep(1000);

  const letterLen = await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      return ta ? 'Length: ' + ta.value.length : 'no textarea';
    })()
  `);
  console.log('Cover letter:', letterLen);

  // Check for rate-increase section errors and fix them
  console.log('\n=== CHECKING RATE INCREASE SECTION ===');
  const rateIncrease = await c.ev(`
    (() => {
      // Look for the rate increase dropdowns
      const freqDropdown = [...document.querySelectorAll('[role="combobox"], select')]
        .find(el => el.closest('[class*="rate-increase"]') || el.getAttribute('aria-labelledby')?.includes('frequency'));
      const text = document.body.innerText;
      const hasRateIncrease = text.includes('Schedule a rate increase');
      const hasFreqError = text.includes('rate-increase frequency');
      const hasPercentError = text.includes('rate-increase percent');

      // Find dropdowns in the rate increase section
      const allDropdowns = [...document.querySelectorAll('[role="combobox"]')]
        .filter(d => d.offsetParent)
        .map(d => ({
          text: d.textContent.trim().substring(0, 40),
          ariaLabelledBy: d.getAttribute('aria-labelledby'),
          class: d.className.substring(0, 60)
        }));

      return JSON.stringify({ hasRateIncrease, hasFreqError, hasPercentError, allDropdowns });
    })()
  `);
  console.log(rateIncrease);

  // The rate increase section errors - we need to either:
  // 1. Not trigger the rate increase section at all (don't interact with it)
  // 2. Or properly fill it out
  // Since this is a fresh page load, the errors shouldn't be there yet
  // Let me check if there are any errors
  const currentErrors = await c.ev(`
    (() => {
      const errors = [...document.querySelectorAll('[class*="error"], [role="alert"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 80));
      return JSON.stringify(errors);
    })()
  `);
  console.log('Current errors:', currentErrors);

  // Submit
  console.log('\n=== SUBMITTING ===');
  const preSubmit = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      return JSON.stringify({
        text: sendBtn?.textContent?.trim(),
        disabled: sendBtn?.disabled,
        rate: document.getElementById('step-rate')?.value
      });
    })()
  `);
  console.log('Pre-submit:', preSubmit);

  const submitted = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (sendBtn && !sendBtn.disabled) {
        sendBtn.click();
        return 'Clicked Send';
      }
      return 'Cannot submit';
    })()
  `);
  console.log(submitted);
  await sleep(8000);

  // Check result
  const result = await c.ev(`
    (() => {
      const url = window.location.href;
      const text = document.body.innerText.substring(0, 2000);
      const hasSuccess = text.toLowerCase().includes('submitted') || text.toLowerCase().includes('congratulations') || text.toLowerCase().includes('proposal sent');
      const hasError = text.includes('fix the errors');
      return JSON.stringify({ url, hasSuccess, hasError, excerpt: text.substring(0, 800) });
    })()
  `);
  console.log('\nResult:', result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
