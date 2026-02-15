// Apply to more Upwork jobs - v4 with all fixes
// Handles: beforeunload dialogs, rate increase dropdowns, fixed vs hourly forms, verification walls
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

async function safeNav(c, url) {
  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
  await sleep(200);
  await c.ev(`window.location.href = ${JSON.stringify(url)}`);
}

// Fill rate increase dropdowns for hourly jobs
async function fillRateIncrease(c) {
  const combos = await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      var vis = [];
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent) vis.push(combos[i].textContent.trim());
      }
      return JSON.stringify(vis);
    })()
  `);
  const comboTexts = JSON.parse(combos);

  // Only fill if we see the rate increase dropdowns
  if (!comboTexts.some(t => t.includes('Select a frequency') || t.includes('Select a percent'))) return;

  // Click frequency
  await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent && combos[i].textContent.trim().includes('Select a frequency')) {
          combos[i].click(); return 'ok';
        }
      }
    })()
  `);
  await sleep(500);
  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === 'Every 3 months') { opts[i].click(); return; }
      }
    })()
  `);
  await sleep(500);

  // Click percent
  await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent && combos[i].textContent.trim().includes('Select a percent')) {
          combos[i].click(); return 'ok';
        }
      }
    })()
  `);
  await sleep(500);
  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === '5%') { opts[i].click(); return; }
      }
    })()
  `);
  await sleep(500);
}

// Handle fixed-price form
async function fillFixedPrice(c) {
  // Select "By project" mode
  await c.ev(`
    (() => {
      var radios = document.querySelectorAll('input[name="milestoneMode"]');
      for (var i = 0; i < radios.length; i++) {
        if (radios[i].value === 'default') { radios[i].click(); return; }
      }
    })()
  `);
  await sleep(1000);

  // Set duration
  await c.ev(`
    (() => {
      var combos = document.querySelectorAll('[role="combobox"]');
      for (var i = 0; i < combos.length; i++) {
        if (combos[i].offsetParent && combos[i].textContent.trim().includes('Select')) {
          combos[i].click(); return 'opened';
        }
      }
    })()
  `);
  await sleep(500);
  await c.ev(`
    (() => {
      var opts = document.querySelectorAll('[role="option"]');
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === 'Less than 1 month') { opts[i].click(); return; }
      }
      for (var i = 0; i < opts.length; i++) {
        if (opts[i].textContent.trim() === '1 to 3 months') { opts[i].click(); return; }
      }
    })()
  `);
  await sleep(500);
}

async function applyToJob(c, job, coverLetter) {
  console.log(`\n${'='.repeat(50)}`);
  console.log(`APPLYING: ${job.title.substring(0, 55)}`);
  console.log(`${'='.repeat(50)}`);

  await safeNav(c, job.href);
  await sleep(5000);

  // Check already applied
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 1000)`);
  if (pageText.includes('already submitted')) { console.log('  SKIP: Already applied'); return 'already'; }

  // Click Apply
  const applyBtn = await c.ev(`
    (() => {
      var els = document.querySelectorAll('button, a');
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim().toLowerCase();
        if (els[i].offsetParent && (t === 'apply now' || t === 'submit a proposal')) {
          els[i].click();
          return 'Clicked: ' + els[i].textContent.trim();
        }
      }
      return 'none';
    })()
  `);
  console.log('  Apply:', applyBtn);
  if (applyBtn === 'none') return 'no_button';
  await sleep(6000);

  // Check verification
  const url = await c.ev('window.location.href');
  if (url.includes('verification') || url.includes('step-up')) {
    console.log('  SKIP: Verification required');
    return 'verification';
  }

  // Check if form loaded
  const formCheck = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 200)`);
  const isFixed = formCheck.includes('Fixed-price') || formCheck.includes('milestone');

  // Find textarea
  const hasTa = await c.ev(`
    (() => {
      var tas = document.querySelectorAll('textarea');
      for (var i = 0; i < tas.length; i++) {
        if (tas[i].offsetParent) { tas[i].focus(); return true; }
      }
      return false;
    })()
  `);
  if (!hasTa) { console.log('  SKIP: No textarea'); return 'no_textarea'; }

  // Type cover letter
  await c.selectAll();
  await sleep(100);
  await c.typeText(coverLetter);
  console.log(`  Typed ${coverLetter.length} chars`);
  await sleep(500);

  // Handle form type
  if (isFixed) {
    console.log('  Fixed-price form detected');
    await fillFixedPrice(c);
  } else {
    await fillRateIncrease(c);
  }

  // Submit
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
      return 'none';
    })()
  `);
  console.log('  Submit:', submitted);
  if (submitted === 'none') return 'no_submit';
  await sleep(8000);

  const resultUrl = await c.ev('window.location.href');
  if (resultUrl.includes('success') || resultUrl.includes('edit')) {
    console.log('  SUCCESS!');
    return 'applied';
  }

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

// More relevant jobs from the list
const moreJobs = [
  {
    index: 9, // Autodesk Revit Customization Engineer (C#)
    coverLetter: `Hi — I'm a Revit Customization Engineer with production C# add-in experience across Revit 2024-2026.

What I deliver:
• Custom Revit API plugins in C# with ribbon UI
• Database integration (SQL Server, SQLite)
• Batch processing and data extraction tools
• Full Visual Studio solutions with documentation

I can start immediately. What customization workflows are you targeting?`
  },
  {
    index: 8, // Build a Dynamo Script - Object properties in Revit 2021
    coverLetter: `Hi — I'm a Dynamo and Revit specialist. I can build a Dynamo script to automate updating object instance properties in Revit 2021.

My experience:
• Custom Dynamo scripts with Python nodes
• Parameter management and batch updates
• Revit API integration for complex logic
• Testing across Revit 2021-2026

What properties need updating, and are they instance or type parameters?`
  },
  {
    index: 19, // C# web page parser
    coverLetter: `Hi — I'm a C# .NET developer with web scraping and HTML parsing experience. I build clean, maintainable parser tools using HtmlAgilityPack, AngleSharp, or HttpClient with regex.

Skills:
• C# .NET Framework web scraping
• HTML parsing with HtmlAgilityPack/AngleSharp
• Windows desktop applications
• Data extraction and transformation

What websites do you need parsed, and what data format do you need?`
  },
  {
    index: 1, // Revit 2025 add-in
    coverLetter: `Hi — I'm a Revit C# add-in developer with production experience across Revit 2024, 2025, and 2026.

What I deliver:
• C# Revit API add-ins compiled for Revit 2025
• Custom ribbon UI with WPF dialogs
• Named Pipes IPC for real-time communication
• Full Visual Studio solution with docs

What does the add-in need to do?`
  }
];

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const jobs = JSON.parse(readFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', 'utf8'));
  console.log(`Loaded ${jobs.length} jobs, applying to ${moreJobs.length} more`);

  let results = { applied: 0, already: 0, failed: 0 };

  for (const target of moreJobs) {
    const job = jobs[target.index];
    if (!job) { console.log(`Job ${target.index} not found`); results.failed++; continue; }

    try {
      const result = await applyToJob(c, job, target.coverLetter);
      if (result === 'applied') results.applied++;
      else if (result === 'already') results.already++;
      else results.failed++;
    } catch (e) {
      console.log('  ERROR:', e.message);
      results.failed++;
    }
    try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
    await sleep(2000);
  }

  console.log(`\n${'='.repeat(50)}`);
  console.log(`RESULTS: Applied: ${results.applied} | Already: ${results.already} | Failed: ${results.failed}`);
  console.log(`${'='.repeat(50)}`);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
