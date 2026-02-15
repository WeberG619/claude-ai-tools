// Apply to Upwork jobs - v3: fixes Leave Page dialog + submit button detection
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
      // Auto-handle "Leave this page?" dialogs
      if (msg.method === 'Page.javascriptDialogOpening') {
        console.log('  [Dialog detected: "' + (msg.params?.message || '').substring(0, 50) + '"] Auto-accepting...');
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
      // Enable Page domain to receive dialog events
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

// Safe navigation - clears beforeunload first, then navigates
async function safeNavigate(c, url) {
  try {
    await c.ev(`window.onbeforeunload = null`);
  } catch (e) { /* ignore if page context is gone */ }
  await sleep(200);
  await c.ev(`window.location.href = ${JSON.stringify(url)}`);
}

const targetJobs = [
  {
    index: 2, // Autodesk Automation API
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
    index: 3, // Dynamo Revit Script Review
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
    index: 5, // Licensing System for Revit Plugins
    coverLetter: `Hi — this project is a perfect fit. I build Revit C# plugins professionally and understand both the plugin side (Revit API, .addin manifests, deployment) and the web side (ASP.NET, C#, Stripe integration).

Relevant experience:
• Production Revit plugins with licensing/activation systems
• ASP.NET web applications with Stripe payment integration
• C#/.NET full-stack development
• Plugin deployment, updates, and version management

I can architect the complete system — web platform for license management + e-commerce, plus plugin-side license validation. I understand the specific challenges of Revit plugin licensing (offline validation, version-specific loading, etc.).

What licensing model are you targeting — per-seat, subscription, or one-time?`
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
    index: 10, // NWC export plugin
    coverLetter: `Hi — I build Revit plugins in C# and have experience with Navisworks export automation. I can create an add-in that batch-exports NWC files per workset with your required settings.

My approach:
• C# Revit API add-in with custom ribbon button
• Configurable NWC export options per workset
• Batch processing for multiple views/models
• Simple WPF interface for user configuration
• Full source code, DLL, .addin file, and docs included

I support Revit 2024-2026 and can test in your target version. This is a focused project I can deliver within a week.

What specific export settings and workset handling do you need?`
  },
  {
    index: 33, // ACC API Cloud
    coverLetter: `Hi — I'm a .NET/C# developer with Autodesk cloud API experience (APS/ACC). I work with both the desktop Revit API and cloud-based Autodesk Construction Cloud services.

Relevant skills:
• C#/.NET 4.8 development (matching your stack)
• Autodesk Platform Services — ACC, BIM 360 APIs
• OAuth authentication flows for Autodesk APIs
• Document management and data sync between ACC and local systems

I build clean, well-documented code and can start immediately. What specific ACC API workflows are you implementing?`
  },
  {
    index: 7, // BIM Manager
    coverLetter: `Hi — I'm a BIM specialist with strong C#/.NET and Revit API skills. I develop custom automation tools, manage BIM workflows, and build add-ins for clash detection, data extraction, and model coordination.

Skills:
• Revit API (C#/.NET Core and .NET Framework)
• BIM coordination and clash detection automation
• Custom ribbon tools and workflow automation
• Data extraction and reporting from Revit models

Available for ongoing BIM management support. What specific BIM challenges are you looking to solve?`
  },
  {
    index: 38, // Dynamo for Revit - Gym Design
    coverLetter: `Hi — I'm a Dynamo and Revit specialist with C# and Python expertise. I can build custom Dynamo scripts for your gym design projects — layout automation, equipment placement, space planning, or parameter-driven design.

Experience:
• Custom Dynamo scripts for Revit automation
• Python nodes for complex logic
• C# Revit API plugins that extend Dynamo capabilities
• Parametric design and space planning automation

What specific aspects of the gym design workflow are you looking to automate with Dynamo?`
  }
];

async function applyToJob(c, job, coverLetter) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`APPLYING: ${job.title.substring(0, 60)}`);
  console.log(`${'='.repeat(60)}`);

  // Safe navigate to job page (clears beforeunload first)
  await safeNavigate(c, job.href);
  await sleep(5000);

  // Check if already applied
  const alreadyApplied = await c.ev(`
    (document.querySelector('main') || document.body).innerText.includes('already submitted')
  `);
  if (alreadyApplied) {
    console.log('SKIP: Already applied');
    return 'already_applied';
  }

  // Find Apply now button (case-insensitive)
  const applyBtn = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, a');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && (t === 'apply now' || t === 'submit a proposal' || t === 'submit proposal')) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'No apply button found';
    })()
  `);
  console.log('Apply:', applyBtn);

  if (applyBtn.includes('No apply')) return 'no_button';
  await sleep(6000);

  // Check if we hit a verification wall
  const url = await c.ev('window.location.href');
  console.log('URL:', url);
  if (url.includes('verification') || url.includes('step-up')) {
    console.log('SKIP: Verification required');
    return 'verification_required';
  }

  // Check the proposal form
  const formText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log('Form preview:', formText.substring(0, 300));

  // Find cover letter textarea
  const taInfo = await c.ev(`
    (() => {
      var textareas = document.querySelectorAll('textarea');
      var result = [];
      for (var i = 0; i < textareas.length; i++) {
        if (textareas[i].offsetParent) {
          result.push({
            id: textareas[i].id || '',
            name: textareas[i].name || '',
            placeholder: (textareas[i].placeholder || '').substring(0, 50)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);
  console.log('Textareas:', taInfo);

  const textareas = JSON.parse(taInfo);
  if (textareas.length === 0) {
    console.log('SKIP: No textarea on form');
    return 'no_textarea';
  }

  // Focus the cover letter textarea
  const focused = await c.ev(`
    (() => {
      var textareas = document.querySelectorAll('textarea');
      for (var i = 0; i < textareas.length; i++) {
        if (textareas[i].offsetParent) {
          textareas[i].focus();
          return 'Focused: ' + (textareas[i].id || textareas[i].name || 'textarea-' + i);
        }
      }
      return 'none';
    })()
  `);
  console.log('Focus:', focused);

  if (focused === 'none') return 'no_focus';

  await c.selectAll();
  await sleep(100);
  await c.typeText(coverLetter);
  console.log('Typed cover letter (' + coverLetter.length + ' chars)');
  await sleep(1000);

  // Scroll down to find Submit button
  await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(1000);

  // Dump ALL visible buttons to diagnose submit button issue
  const allBtns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent) {
          result.push({
            text: btns[i].textContent.trim().substring(0, 60),
            disabled: btns[i].disabled,
            type: btns[i].type || '',
            classes: (typeof btns[i].className === 'string' ? btns[i].className : '').substring(0, 80)
          });
        }
      }
      return JSON.stringify(result, null, 1);
    })()
  `);
  console.log('ALL visible buttons:', allBtns);

  // Try broader submit button matching
  const submitted = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (btns[i].offsetParent && !btns[i].disabled) {
          // Match any button that looks like a submit/send action
          if (t.includes('submit') || t.includes('send') || t.includes('yes,') ||
              (t === 'apply' && btns[i].type === 'submit')) {
            btns[i].click();
            return 'Clicked: ' + btns[i].textContent.trim();
          }
        }
      }
      // Also try input[type=submit]
      var inputs = document.querySelectorAll('input[type="submit"]');
      for (var j = 0; j < inputs.length; j++) {
        if (inputs[j].offsetParent && !inputs[j].disabled) {
          inputs[j].click();
          return 'Clicked input: ' + inputs[j].value;
        }
      }
      return 'No submit button';
    })()
  `);
  console.log('Submit:', submitted);

  if (submitted.includes('No submit')) {
    // Try clicking the primary/green button as last resort
    const primaryBtn = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button.air3-btn-primary, button[data-qa*="submit"], button[data-qa*="send"]');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && !btns[i].disabled) {
            btns[i].click();
            return 'Clicked primary: ' + btns[i].textContent.trim();
          }
        }
        return 'No primary button';
      })()
    `);
    console.log('Primary fallback:', primaryBtn);
    if (primaryBtn.includes('No primary')) return 'no_submit';
  }

  await sleep(8000);

  // Check for confirmation dialog (like "are you sure?")
  const confirmBtn = await c.ev(`
    (() => {
      var dialogs = document.querySelectorAll('[role="dialog"], .modal, [class*="modal"]');
      for (var d = 0; d < dialogs.length; d++) {
        if (dialogs[d].offsetParent) {
          var btns = dialogs[d].querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t.includes('yes') || t.includes('confirm') || t.includes('submit') || t.includes('send')) {
              btns[i].click();
              return 'Confirmed: ' + btns[i].textContent.trim();
            }
          }
        }
      }
      return 'no dialog';
    })()
  `);
  if (confirmBtn !== 'no dialog') {
    console.log('Confirmation:', confirmBtn);
    await sleep(5000);
  }

  // Check result
  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
  console.log('Result URL:', resultUrl);
  console.log('Result:', resultText.substring(0, 200));

  return 'applied';
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Wait for Page.enable to take effect
  await sleep(500);

  const jobs = JSON.parse(readFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', 'utf8'));
  console.log(`Loaded ${jobs.length} jobs, applying to ${targetJobs.length}`);

  let results = { applied: 0, already: 0, failed: 0, verification: 0 };

  for (const target of targetJobs) {
    const job = jobs[target.index];
    if (!job) { console.log(`Job ${target.index} not found`); results.failed++; continue; }

    try {
      const result = await applyToJob(c, job, target.coverLetter);
      if (result === 'applied') results.applied++;
      else if (result === 'already_applied') results.already++;
      else if (result === 'verification_required') results.verification++;
      else results.failed++;
    } catch (e) {
      console.log('ERROR:', e.message);
      results.failed++;
    }
    // Clear beforeunload before moving to next job
    try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
    await sleep(2000);
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`RESULTS: Applied: ${results.applied} | Already: ${results.already} | Verification: ${results.verification} | Failed: ${results.failed}`);
  console.log(`${'='.repeat(60)}`);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
