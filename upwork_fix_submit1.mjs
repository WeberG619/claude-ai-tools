// Fix rate and cover letter, then submit proposal for Revit 2025 add-in
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

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Fix the rate - triple-click to select all text in the input, then clear and retype
  console.log('\n=== FIXING RATE ===');

  // Focus and fully clear the rate input
  await c.ev(`
    (() => {
      const input = document.getElementById('step-rate');
      if (input) {
        input.focus();
        input.select();
      }
    })()
  `);
  await sleep(300);
  await c.selectAll();
  await sleep(200);

  // Delete current content
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
  await sleep(300);

  // Type the rate
  await c.typeText('85');
  await sleep(500);

  // Tab to trigger update
  await c.pressTab();
  await sleep(1000);

  // Check rate
  const rateCheck = await c.ev(`
    (() => {
      return JSON.stringify({
        rate: document.getElementById('step-rate')?.value,
        fee: document.getElementById('fee-rate')?.value,
        receive: document.getElementById('receive-step-rate')?.value
      });
    })()
  `);
  console.log('Rates:', rateCheck);

  // Fix cover letter
  console.log('\n=== FIXING COVER LETTER ===');
  await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      if (ta) {
        ta.focus();
        ta.select();
      }
    })()
  `);
  await sleep(300);
  await c.selectAll();
  await sleep(200);
  // Delete existing content
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
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

  // Verify cover letter
  const letterLen = await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      return ta ? 'Length: ' + ta.value.length + ' | Start: ' + ta.value.substring(0, 80) : 'no textarea';
    })()
  `);
  console.log('Cover letter:', letterLen);

  // Check for any errors
  console.log('\n=== ERROR CHECK ===');
  const errors = await c.ev(`
    (() => {
      const errorEls = [...document.querySelectorAll('[class*="error"], [class*="alert"], [role="alert"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify(errorEls);
    })()
  `);
  console.log('Errors:', errors);

  // Pre-submit state
  console.log('\n=== PRE-SUBMIT ===');
  const preSubmit = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      return JSON.stringify({
        btnText: sendBtn?.textContent?.trim(),
        disabled: sendBtn?.disabled,
        rate: document.getElementById('step-rate')?.value
      });
    })()
  `);
  console.log(preSubmit);

  // Submit
  console.log('\n=== SUBMITTING ===');
  const sent = await c.ev(`
    (() => {
      const sendBtn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (sendBtn && !sendBtn.disabled) {
        sendBtn.click();
        return 'Submitted';
      }
      return 'Cannot submit: ' + (sendBtn ? 'disabled' : 'not found');
    })()
  `);
  console.log(sent);
  await sleep(5000);

  // Check result
  const result = await c.ev(`
    (() => {
      const url = window.location.href;
      const hasSuccess = document.body.innerText.includes('proposal') && document.body.innerText.includes('submitted');
      const hasError = document.body.innerText.includes('fix the errors');
      const mainText = (document.querySelector('main') || document.body).innerText.substring(0, 1500);
      return JSON.stringify({ url, hasSuccess, hasError, text: mainText });
    })()
  `);
  console.log('\nResult:', result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
