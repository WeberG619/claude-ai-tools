// Apply to Job 2: Plugin Developer - Named Pipes
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

  // Navigate to job 2
  console.log('=== NAVIGATING TO JOB 2 ===');
  await c.nav('https://www.upwork.com/jobs/Plugin-Developer-NET-Python-ArchiCAD-AutoCAD-Image-Streaming-via-Windows-Pipes_~022021708919476426386/');
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

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Check the application form
  console.log('\n=== FORM DETAILS ===');
  const formDetails = await c.ev(`
    (() => {
      const main = document.querySelector('main') || document.body;
      const text = main.innerText;

      // Check for screening questions
      const questions = [...main.querySelectorAll('textarea, input[type="text"]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          tag: el.tagName,
          type: el.type,
          id: el.id,
          placeholder: el.placeholder?.substring(0, 40),
          label: el.closest('.air3-form-group, [class*="form-group"]')?.querySelector('label')?.textContent?.trim()?.substring(0, 80)
        }));

      // Check for the rate/connects
      const rate = document.getElementById('step-rate')?.value;
      const connects = text.match(/(\\d+)\\s*Connects/)?.[0];

      return JSON.stringify({ rate, connects, questions, textExcerpt: text.substring(0, 500) });
    })()
  `);
  console.log(formDetails);

  // Check rate - should default to $85
  const rate = await c.ev(`document.getElementById('step-rate')?.value`);
  console.log('Rate:', rate);

  // Set rate increase dropdowns immediately to avoid the error
  console.log('\n=== SETTING RATE INCREASE ===');

  // Set frequency
  await c.ev(`
    (() => {
      const dd = [...document.querySelectorAll('[role="combobox"]')]
        .find(d => d.textContent.trim().includes('Select a frequency'));
      if (dd) dd.click();
    })()
  `);
  await sleep(800);
  await c.ev(`
    (() => {
      const option = [...document.querySelectorAll('[role="option"]')]
        .find(o => o.offsetParent && o.textContent.trim() === 'Every 12 months');
      if (option) { option.click(); return 'Selected: Every 12 months'; }
      return 'not found';
    })()
  `);
  await sleep(800);

  // Set percent
  await c.ev(`
    (() => {
      const dd = [...document.querySelectorAll('[role="combobox"]')]
        .find(d => d.textContent.trim().includes('Select a percent'));
      if (dd) dd.click();
    })()
  `);
  await sleep(800);
  const pctSet = await c.ev(`
    (() => {
      const option = [...document.querySelectorAll('[role="option"]')]
        .find(o => o.offsetParent && o.textContent.trim().includes('5%'));
      if (option) { option.click(); return 'Selected: 5%'; }
      const options = [...document.querySelectorAll('[role="option"]')].filter(o => o.offsetParent);
      if (options.length > 0) { options[0].click(); return 'Selected first: ' + options[0].textContent.trim(); }
      return 'no options';
    })()
  `);
  console.log('Percent:', pctSet);
  await sleep(500);

  // Write cover letter
  console.log('\n=== WRITING COVER LETTER ===');
  await c.ev(`
    (() => {
      // Find the main cover letter textarea (not screening question textareas)
      const textareas = [...document.querySelectorAll('textarea')].filter(t => t.offsetParent);
      // The cover letter textarea is usually the first one or the largest one
      if (textareas.length > 0) textareas[0].focus();
    })()
  `);
  await sleep(300);

  const coverLetter = `This job is an excellent match for my skillset - I have direct, hands-on experience with exactly the architecture you're describing.

I built RevitMCPBridge (open-source on GitHub), a production plugin that connects AI assistants to Autodesk Revit using Windows named pipes for IPC. The architecture is very similar to what you need: a lightweight plugin inside the host application captures data and streams it to an external Windows application via named pipes, with non-blocking UI and clean async communication.

Relevant experience:
- Named pipes IPC between .NET plugin and external app (this is my core expertise)
- AutoCAD API plugin development
- C#/.NET desktop development on Windows
- Python scripting for automation
- Viewport and rendering pipeline interaction via host APIs
- WPF/XAML panel creation inside host applications

Tech stack: C#, .NET, Python, named pipes, WPF, Win32 IPC

I can start with AutoCAD as the initial proof of concept since I already know the API, then extend to the other platforms. I'm comfortable working with plugin SDKs and have experience with async image buffer handling.

Happy to share my GitHub portfolio and discuss the technical approach in detail.`;

  await c.typeText(coverLetter);
  await sleep(1000);

  const letterLen = await c.ev(`
    (() => {
      const ta = [...document.querySelectorAll('textarea')].find(t => t.offsetParent);
      return ta ? ta.value.length : 0;
    })()
  `);
  console.log('Cover letter length:', letterLen);

  // Check for errors before submit
  const preErrors = await c.ev(`
    (() => {
      return [...document.querySelectorAll('[class*="error"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim().substring(0, 80));
    })()
  `);
  console.log('Pre-submit errors:', JSON.stringify(preErrors));

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

  // Wait for result
  for (let i = 0; i < 10; i++) {
    await sleep(2000);
    const currentUrl = await c.ev('window.location.href');
    if (!currentUrl.includes('apply')) {
      console.log(`\nSUCCESS after ${(i+1)*2}s! URL: ${currentUrl}`);
      const text = await c.ev('document.body.innerText.substring(0, 500)');
      console.log(text);
      c.close();
      process.exit(0);
    }

    // Check for modal overlay
    const hasModal = await c.ev(`
      (() => {
        const modal = document.querySelector('.air3-modal');
        if (modal && getComputedStyle(modal).display !== 'none') {
          // Try to close it
          const closeBtn = modal.querySelector('.air3-modal-close');
          if (closeBtn) closeBtn.click();
          return 'Closed modal';
        }
        return null;
      })()
    `);
    if (hasModal) console.log(`${(i+1)*2}s: ${hasModal}`);
    else console.log(`Waiting... ${(i+1)*2}s`);
  }

  // Still on apply page - check errors
  console.log('\n=== CHECKING ERRORS ===');
  const finalErrors = await c.ev(`
    (() => {
      return [...document.querySelectorAll('[class*="error"], [class*="alert-negative"]')]
        .filter(el => el.offsetParent && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim().substring(0, 100));
    })()
  `);
  console.log(JSON.stringify(finalErrors));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
