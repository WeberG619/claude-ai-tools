// Fill and submit proposal for Revit 2025 add-in
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Should already be on the proposal page
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  if (!url.includes('proposals') && !url.includes('apply')) {
    console.log('Not on proposal page, navigating...');
    await c.nav('https://www.upwork.com/nx/proposals/job/~022021630179255436296/apply/');
    await sleep(5000);
  }

  // Step 1: Set hourly rate to $85
  console.log('\n=== SETTING RATE ===');
  const rateSet = await c.ev(`
    (() => {
      const rateInput = document.getElementById('step-rate');
      if (rateInput) {
        rateInput.focus();
        return 'Focused rate input, current value: ' + rateInput.value;
      }
      return 'Rate input not found';
    })()
  `);
  console.log(rateSet);
  await sleep(200);
  await c.selectAll();
  await sleep(100);
  await c.typeText('85');
  await sleep(500);

  // Tab away to trigger calculation
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
  await sleep(1000);

  // Verify rates
  const rates = await c.ev(`
    (() => {
      return JSON.stringify({
        hourlyRate: document.getElementById('step-rate')?.value,
        fee: document.getElementById('fee-rate')?.value,
        receive: document.getElementById('receive-step-rate')?.value
      });
    })()
  `);
  console.log('Rates:', rates);

  // Step 2: Write cover letter
  console.log('\n=== WRITING COVER LETTER ===');
  const coverLetterFocused = await c.ev(`
    (() => {
      const textareas = [...document.querySelectorAll('textarea')].filter(t => t.offsetParent);
      if (textareas.length > 0) {
        textareas[0].focus();
        return 'Focused textarea: ' + textareas[0].placeholder?.substring(0, 40);
      }
      return 'No textarea found';
    })()
  `);
  console.log(coverLetterFocused);
  await sleep(300);

  const coverLetter = `I build Revit add-ins daily and this is a straightforward project I can deliver quickly.

Relevant experience:
- I develop C# Revit API plugins professionally, working in Revit 2025/2026 every day
- I built RevitMCPBridge (open-source on GitHub) — a full IPC bridge between AI assistants and Revit using named pipes and the Revit API
- Experienced with adaptive components, placement APIs, and element selection workflows

For your add-in, I'd implement:
- A ribbon button that triggers a selection workflow (PickObject for each adaptive point)
- Placement of the 2-point adaptive family using AdaptiveComponentInstanceUtils
- Proper adaptive point assignment so the profile follows when points move

I can have a working prototype within 2-3 days, with the complete Visual Studio solution, compiled DLL, .addin file, and documentation.

Happy to discuss approach or answer questions before starting.`;

  await c.typeText(coverLetter);
  await sleep(1000);

  // Verify the cover letter was typed
  const letterCheck = await c.ev(`
    (() => {
      const textareas = [...document.querySelectorAll('textarea')].filter(t => t.offsetParent);
      if (textareas[0]) return textareas[0].value.substring(0, 100) + '... (length: ' + textareas[0].value.length + ')';
      return 'no textarea';
    })()
  `);
  console.log('Cover letter check:', letterCheck);

  // Step 3: Check full page state before submitting
  console.log('\n=== PRE-SUBMIT STATE ===');
  const preSubmit = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      return JSON.stringify({
        sendButtonText: sendBtn?.textContent?.trim() || 'not found',
        sendButtonDisabled: sendBtn?.disabled,
        url: window.location.href
      });
    })()
  `);
  console.log(preSubmit);

  // Submit the proposal
  console.log('\n=== SUBMITTING PROPOSAL ===');
  const submitted = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (sendBtn && !sendBtn.disabled) {
        sendBtn.click();
        return 'Clicked: ' + sendBtn.textContent.trim();
      }
      return sendBtn ? 'Button disabled' : 'Send button not found';
    })()
  `);
  console.log(submitted);
  await sleep(5000);

  // Check result
  const afterSubmit = await c.ev(`
    (() => {
      const url = window.location.href;
      const text = document.body.innerText.substring(0, 1500);
      return 'URL: ' + url + '\\n\\n' + text;
    })()
  `);
  console.log('\n=== AFTER SUBMIT ===');
  console.log(afterSubmit);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
