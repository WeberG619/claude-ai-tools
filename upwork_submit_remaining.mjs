// Submit remaining proposals that had rate-increase errors
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
import { readFileSync } from 'fs';

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
      if (msg.method === 'Page.javascriptDialogOpening') {
        console.log('  [Auto-accepting dialog]');
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(4);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function safeNavigate(c, url) {
  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
  await sleep(200);
  await c.ev(`window.location.href = ${JSON.stringify(url)}`);
}

async function fillRateIncrease(c) {
  // Click frequency dropdown and select "Every 3 months"
  const combo1 = await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      var visible = [];
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) visible.push(combos[i]);
      }
      if (visible.length >= 1) {
        visible[0].click();
        return 'opened';
      }
      return 'none';
    })()
  `);
  if (combo1 === 'none') return;
  await sleep(500);

  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === 'Every 3 months') {
          opts[i].click();
          return 'selected';
        }
      }
      return 'not found';
    })()
  `);
  await sleep(500);

  // Click percent dropdown and select "5%"
  const combo2 = await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      var visible = [];
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) visible.push(combos[i]);
      }
      if (visible.length >= 2) {
        visible[1].click();
        return 'opened';
      }
      return 'none';
    })()
  `);
  if (combo2 === 'none') return;
  await sleep(500);

  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === '5%') {
          opts[i].click();
          return 'selected';
        }
      }
      return 'not found';
    })()
  `);
  await sleep(500);
  console.log('  Rate increase set: Every 3 months, 5%');
}

async function applyToJob(c, job, coverLetter) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`APPLYING: ${job.title.substring(0, 60)}`);
  console.log(`${'='.repeat(60)}`);

  await safeNavigate(c, job.href);
  await sleep(5000);

  // Check if already applied
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1000)`);
  if (pageText.includes('already submitted') || pageText.includes('Your proposal was submitted')) {
    console.log('SKIP: Already applied');
    return 'already_applied';
  }

  // Find and click Apply now
  const applyBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, a');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t === 'apply now' || t === 'submit a proposal')) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'No apply button';
    })()
  `);
  console.log('  Apply:', applyBtn);
  if (applyBtn.includes('No apply')) return 'no_button';
  await sleep(6000);

  // Check for verification
  const url = await c.ev('window.location.href');
  if (url.includes('verification') || url.includes('step-up')) {
    console.log('  SKIP: Verification required');
    return 'verification';
  }

  // Check for textarea
  const hasTA = await c.ev(`
    (() => {
      var tas = document.querySelectorAll('textarea');
      for (var i = 0; i < tas.length; i++) {
        if (tas[i].offsetParent) { tas[i].focus(); return true; }
      }
      return false;
    })()
  `);
  if (!hasTA) { console.log('  SKIP: No textarea'); return 'no_textarea'; }

  // Type cover letter
  await c.selectAll();
  await sleep(100);
  await c.typeText(coverLetter);
  console.log(`  Typed ${coverLetter.length} chars`);
  await sleep(500);

  // Fill rate increase dropdowns
  await fillRateIncrease(c);

  // Scroll down and submit
  await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(500);

  const submitted = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && !btns[i].disabled && (t.includes('submit') || t.includes('send'))) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'no submit';
    })()
  `);
  console.log('  Submit:', submitted);
  await sleep(8000);

  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 300)`);
  console.log('  Result URL:', resultUrl);

  if (resultUrl.includes('success') || resultText.includes('proposal was submitted')) {
    console.log('  SUCCESS!');
    return 'applied';
  } else {
    console.log('  Result:', resultText.substring(0, 200));
    // Check for errors
    const errors = await c.ev(`
      (() => {
        var errs = document.querySelectorAll('.air3-form-message-error');
        var r = [];
        for (var i = 0; i < errs.length; i++) {
          if (errs[i].offsetParent) r.push(errs[i].textContent.trim());
        }
        return JSON.stringify(r);
      })()
    `);
    console.log('  Errors:', errors);
    return 'error';
  }
}

const remainingJobs = [
  {
    index: 3, // Dynamo Script Review
    coverLetter: `Hi — I specialize in Revit + Dynamo development with strong C# and Python skills. I can review your existing Dynamo scripts, optimize them, and handle the parameter value adjustments you need.

My background:
• Dynamo script development and optimization for Revit
• Python scripting within Dynamo nodes
• C# Revit API plugins that complement Dynamo workflows
• Parameter management and batch value updates

I work with Revit 2023-2026 and can test changes in your target version. Available to start immediately.

Could you share the current scripts so I can give you a more specific estimate?`
  },
  {
    index: 6, // Revit API Data Extraction
    coverLetter: `Hi — I'm a Revit API engineer who specializes in data extraction and ETL from Revit models.

What I've built:
• Custom Revit add-ins that extract element data, parameters, schedules, and geometry
• ETL pipelines from Revit to databases, Excel, and JSON
• Python + C# integration for data processing
• Named Pipes IPC for real-time Revit data streaming

I deliver clean, maintainable C# code with full documentation. My tools handle large models efficiently and support Revit 2024-2026.

What specific data are you extracting, and what's the target schema/destination?`
  },
  {
    index: 2, // Autodesk Automation API (retry - didn't load form before)
    coverLetter: `Hi — I'm a Revit API specialist with deep experience in Autodesk's automation ecosystem. I build production C# add-ins and have worked extensively with the Revit API, Forge/APS Design Automation API, and Dynamo.

What I bring:
• Custom Revit API plugins (C#/.NET) — add-ins, ribbon tools, data extraction, batch processing
• Autodesk Platform Services (APS/Forge) and Design Automation API
• Named Pipes IPC for real-time Revit communication
• Multi-version support (Revit 2024, 2025, 2026)

I deliver complete Visual Studio solutions with source code, compiled DLLs, documentation, and installation guides. I can start immediately.

Happy to discuss your specific automation needs — what Revit workflows are you looking to automate?`
  },
  {
    index: 1, // Revit 2025 add-in (new - recently posted)
    coverLetter: `Hi — I'm a Revit C# add-in developer with production experience across Revit 2024, 2025, and 2026. I build custom ribbon tools, data extraction utilities, and automation add-ins.

What I deliver:
• C# Revit API add-ins compiled for your target version
• Custom ribbon UI with WPF dialogs
• Named Pipes IPC for real-time Revit communication
• Full Visual Studio solution, DLLs, .addin manifest, and documentation

Happy to discuss your requirements. What specifically does the add-in need to do?`
  },
  {
    index: 0, // Plugin Developer - ArchiCAD/AutoCAD (new - 1 hour ago)
    coverLetter: `Hi — I'm a plugin developer specializing in AEC software automation. I build plugins for Revit (C#/.NET) and have experience with Named Pipes IPC for real-time streaming between applications.

Relevant skills:
• C#/.NET plugin development with Windows Pipes IPC
• Desktop application integration and automation
• Image/data streaming via named pipes
• Multi-platform plugin architecture

I understand the streaming pipeline you're describing. What image format and frame rate are you targeting?`
  }
];

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const jobs = JSON.parse(readFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', 'utf8'));
  console.log(`Loaded ${jobs.length} jobs`);

  let results = { applied: 0, already: 0, failed: 0 };

  for (const target of remainingJobs) {
    const job = jobs[target.index];
    if (!job) { console.log(`Job ${target.index} not found`); results.failed++; continue; }

    try {
      const result = await applyToJob(c, job, target.coverLetter);
      if (result === 'applied') results.applied++;
      else if (result === 'already_applied') results.already++;
      else results.failed++;
    } catch (e) {
      console.log('  ERROR:', e.message);
      results.failed++;
    }
    try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
    await sleep(2000);
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`RESULTS: Applied: ${results.applied} | Already: ${results.already} | Failed: ${results.failed}`);
  console.log(`${'='.repeat(60)}`);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
