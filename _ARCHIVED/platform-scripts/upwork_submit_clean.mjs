// Clean submit - fresh page, only fill cover letter, don't touch rate increase
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Navigate to the job page first (not the apply page) to get a clean start
  console.log('=== NAVIGATING TO JOB ===');
  await c.nav('https://www.upwork.com/jobs/Revit-2025-add_~022021630179255436296/');
  await sleep(3000);

  // Click Apply Now
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button, a')].find(el =>
        el.textContent.trim().toLowerCase().includes('apply now') && el.offsetParent
      );
      if (btn) btn.click();
    })()
  `);
  await sleep(5000);

  console.log('URL:', await c.ev('window.location.href'));

  // Verify rate is $85 (don't touch it)
  const rate = await c.ev(`document.getElementById('step-rate')?.value`);
  console.log('Rate:', rate);

  // Check that there are NO errors on the fresh page
  const freshErrors = await c.ev(`
    (() => {
      return [...document.querySelectorAll('[class*="error"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim()).join(' | ');
    })()
  `);
  console.log('Fresh errors:', freshErrors || 'NONE');

  // Only fill the cover letter - focus the textarea directly
  console.log('\n=== FILLING COVER LETTER ===');
  await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      if (ta) ta.focus();
    })()
  `);
  await sleep(300);

  const coverLetter = 'I build Revit add-ins daily and this is a straightforward project I can deliver quickly.\n\nRelevant experience:\n- I develop C# Revit API plugins professionally, working in Revit 2025/2026 every day\n- I built RevitMCPBridge (open-source on GitHub) - a full IPC bridge between AI assistants and Revit using named pipes and the Revit API\n- Experienced with adaptive components, placement APIs, and element selection workflows\n\nFor your add-in, I would implement:\n- A ribbon button that triggers a selection workflow (PickObject for each adaptive point)\n- Placement of the 2-point adaptive family using AdaptiveComponentInstanceUtils\n- Proper adaptive point assignment so the profile follows when points move\n\nI can have a working prototype within 2-3 days, with the complete Visual Studio solution, compiled DLL, .addin file, and documentation.\n\nHappy to discuss approach or answer questions before starting.';

  await c.typeText(coverLetter);
  await sleep(1000);

  // Verify
  const letterCheck = await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      return ta ? 'Length: ' + ta.value.length + ' | OK: ' + (ta.value.length > 500) : 'no textarea';
    })()
  `);
  console.log('Cover letter:', letterCheck);

  // Do NOT interact with rate increase section at all
  // Just scroll down and submit
  console.log('\n=== SUBMITTING ===');
  // Scroll to bottom first
  await c.ev('window.scrollTo(0, document.body.scrollHeight)');
  await sleep(500);

  const preSubmit = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      return btn ? 'Ready: ' + btn.textContent.trim() + ' | disabled: ' + btn.disabled : 'No submit button';
    })()
  `);
  console.log(preSubmit);

  // Click submit
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
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1500)`);
  console.log('\nResult URL:', resultUrl);
  console.log('Result text:', resultText.substring(0, 500));

  // Check if we're still on the apply page (error) or moved somewhere (success)
  if (resultUrl.includes('apply')) {
    console.log('\n=== STILL ON APPLY PAGE - CHECKING ERRORS ===');
    const errors = await c.ev(`
      (() => {
        return [...document.querySelectorAll('[class*="error"], [class*="alert-negative"]')]
          .filter(el => el.offsetParent && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim());
      })()
    `);
    console.log('Errors:', JSON.stringify(errors));

    // Specifically check the rate increase section
    const rateIncState = await c.ev(`
      (() => {
        const dropdowns = [...document.querySelectorAll('[role="combobox"]')].filter(d => d.offsetParent);
        return dropdowns.map(d => ({
          text: d.textContent.trim(),
          hasError: d.className.includes('error')
        }));
      })()
    `);
    console.log('Dropdowns:', JSON.stringify(rateIncState));
  } else {
    console.log('\nSUCCESS - Navigated away from apply page!');
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
