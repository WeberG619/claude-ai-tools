// Apply to multiple Upwork jobs with tailored proposals
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
        await sleep(5);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

// Best matching jobs to apply to (hand-picked from search results)
const targetJobs = [
  {
    index: 2, // Autodesk Automation API and Revit Specialist
    coverLetter: `Hi — I'm a Revit API specialist with deep experience in Autodesk's automation ecosystem. I build production C# add-ins and have worked extensively with the Revit API, Forge/APS, and Dynamo.

What I bring:
• Custom Revit API plugins (C#/.NET) — add-ins, ribbon tools, data extraction, batch processing
• Autodesk Platform Services (APS/Forge) integration
• Named Pipes IPC for real-time Revit communication
• Multi-version support (Revit 2024, 2025, 2026)

I deliver complete Visual Studio solutions with source code, compiled DLLs, documentation, and installation guides. I can start immediately and typically turn around focused Revit automation work within 1-2 weeks.

Happy to discuss your specific automation needs — what Revit version and workflows are you looking to automate?`
  },
  {
    index: 3, // Dynamo Revit Script Review
    coverLetter: `Hi — I specialize in Revit + Dynamo development with strong C# and Python skills. I can review your existing Dynamo scripts, optimize them, and handle the parameter value adjustments you need.

My background:
• Dynamo script development and optimization for Revit
• Python scripting within Dynamo nodes
• C# Revit API plugins that complement Dynamo workflows
• Parameter management and batch value updates

I work with Revit 2024-2026 and can test changes in your target version. I'm available to start immediately and can turn around script reviews quickly.

Could you share the current scripts so I can give you a more specific estimate?`
  },
  {
    index: 5, // Licensing System for Revit Plugins
    coverLetter: `Hi — this project is a perfect fit for my skillset. I build Revit C# plugins professionally and understand both the plugin side (Revit API, .addin manifests, deployment) and the web side (ASP.NET, C#, e-commerce integration).

Relevant experience:
• Production Revit plugins with licensing/activation systems
• ASP.NET web applications with payment integration
• C#/.NET full-stack development
• Plugin deployment, updates, and version management

I can architect and build the complete system — the web platform for license management and e-commerce, plus the plugin-side license validation. I've dealt with the specific challenges of Revit plugin licensing (offline validation, version-specific loading, etc.).

What licensing model are you targeting — per-seat, subscription, or one-time purchase?`
  },
  {
    index: 6, // Revit API Engineer – Data Extraction Tool
    coverLetter: `Hi — I'm a Revit API engineer who specializes in exactly this: building data extraction and ETL tools from Revit models.

What I've built:
• Custom Revit add-ins that extract element data, parameters, schedules, and geometry
• ETL pipelines from Revit to databases, Excel, and JSON
• Python + C# integration for data processing
• Named Pipes IPC for real-time Revit data streaming

I deliver clean, maintainable C# code with full documentation. My tools handle large models efficiently and support Revit 2024-2026.

I can start right away. What specific data are you looking to extract, and what's the target format/destination?`
  },
  {
    index: 10, // Revit Plug-in Exporting NWC files
    coverLetter: `Hi — I build Revit plugins in C# and have experience with Navisworks file export automation. I can create an add-in that batch-exports NWC files with the settings and configurations you need.

My approach:
• C# Revit API add-in with custom ribbon button
• Configurable export settings (NWC export options)
• Batch processing for multiple views/models
• Windows Forms or WPF interface for user control
• Full source code and documentation included

I support Revit 2024-2026 and can test in your target version. This is a focused project I can deliver quickly.

What specific NWC export workflow are you looking to automate?`
  },
  {
    index: 33, // Developer Familiar with ACC API Cloud
    coverLetter: `Hi — I'm a .NET/C# developer with experience in Autodesk's cloud APIs (APS/ACC). I work with both the desktop Revit API and cloud-based Autodesk Construction Cloud services.

Skills relevant to your project:
• C#/.NET development with RESTful API integration
• Autodesk Platform Services (formerly Forge) — ACC, BIM 360
• OAuth authentication flows for Autodesk APIs
• Data extraction and synchronization between ACC and local systems

I build clean, well-documented code and can start immediately. What specific ACC API workflows are you looking to implement?`
  }
];

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Load jobs data
  const jobs = JSON.parse(readFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', 'utf8'));
  console.log(`Loaded ${jobs.length} jobs`);

  let applied = 0;
  let failed = 0;

  for (const target of targetJobs) {
    const job = jobs[target.index];
    if (!job) { console.log(`Job index ${target.index} not found`); continue; }

    console.log(`\n${'='.repeat(60)}`);
    console.log(`APPLYING: ${job.title.substring(0, 70)}`);
    console.log(`${'='.repeat(60)}`);

    // Navigate to the job
    await c.ev(`window.location.href = ${JSON.stringify(job.href)}`);
    await sleep(5000);

    // Check if we can apply
    const pageState = await c.ev(`
      (() => {
        var main = document.querySelector('main') || document.body;
        var text = main.innerText;
        var hasApply = text.includes('Apply Now') || text.includes('Submit a Proposal');
        var alreadyApplied = text.includes('You have already submitted') || text.includes('already applied');
        var applyBtn = null;
        var btns = document.querySelectorAll('a, button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim();
          if (t.includes('Apply Now') || t.includes('Submit a Proposal')) {
            applyBtn = { text: t, href: btns[i].href || '', tag: btns[i].tagName };
          }
        }
        return JSON.stringify({ hasApply, alreadyApplied, applyBtn, excerpt: text.substring(0, 500) });
      })()
    `);
    console.log('Page state:', pageState);

    const state = JSON.parse(pageState);
    if (state.alreadyApplied) {
      console.log('SKIP: Already applied');
      continue;
    }

    if (!state.applyBtn) {
      console.log('SKIP: No Apply button found');
      failed++;
      continue;
    }

    // Click Apply
    if (state.applyBtn.href) {
      await c.ev(`window.location.href = ${JSON.stringify(state.applyBtn.href)}`);
    } else {
      await c.ev(`
        (() => {
          var btns = document.querySelectorAll('a, button');
          for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim().includes('Apply Now') || btns[i].textContent.trim().includes('Submit a Proposal')) {
              btns[i].click();
              return 'Clicked';
            }
          }
        })()
      `);
    }
    await sleep(5000);

    // Check what form appeared
    const formState = await c.ev(`
      (() => {
        var main = document.querySelector('main') || document.body;
        var text = main.innerText.substring(0, 2000);
        var textareas = document.querySelectorAll('textarea');
        var visibleTextareas = [];
        for (var i = 0; i < textareas.length; i++) {
          if (textareas[i].offsetParent) {
            visibleTextareas.push({
              id: textareas[i].id || '',
              placeholder: (textareas[i].placeholder || '').substring(0, 50),
              name: textareas[i].name || ''
            });
          }
        }
        return JSON.stringify({ textareas: visibleTextareas, pageExcerpt: text.substring(0, 800) });
      })()
    `);
    console.log('Form state:', formState);

    const form = JSON.parse(formState);

    // Find the cover letter textarea
    if (form.textareas.length > 0) {
      const coverTA = form.textareas.find(t =>
        t.id.includes('cover') || t.placeholder.includes('cover') ||
        t.name.includes('cover') || t.id.includes('proposal') ||
        t.placeholder.includes('proposal')
      ) || form.textareas[0];

      // Focus and type cover letter
      const focusResult = await c.ev(`
        (() => {
          var ta = document.getElementById('${coverTA.id}');
          if (!ta) {
            var textareas = document.querySelectorAll('textarea');
            for (var i = 0; i < textareas.length; i++) {
              if (textareas[i].offsetParent) { ta = textareas[i]; break; }
            }
          }
          if (ta) { ta.focus(); return 'Focused: ' + ta.id; }
          return 'Not found';
        })()
      `);
      console.log('Focus:', focusResult);

      if (focusResult.includes('Focused')) {
        await c.selectAll();
        await sleep(100);
        await c.typeText(target.coverLetter);
        console.log('Typed cover letter (' + target.coverLetter.length + ' chars)');
        await sleep(1000);

        // Look for Submit/Send Proposal button
        const submitResult = await c.ev(`
          (() => {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (btns[i].offsetParent && !btns[i].disabled &&
                  (t.includes('Submit') || t.includes('Send') || t.includes('Apply'))) {
                // Don't click yet - just report
                return JSON.stringify({
                  text: t,
                  disabled: btns[i].disabled,
                  classes: (typeof btns[i].className === 'string' ? btns[i].className : '').substring(0, 60)
                });
              }
            }
            return 'No submit button found';
          })()
        `);
        console.log('Submit button:', submitResult);

        // Click submit
        const clicked = await c.ev(`
          (() => {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
              var t = btns[i].textContent.trim();
              if (btns[i].offsetParent && !btns[i].disabled &&
                  (t.includes('Send') || t.includes('Submit Proposal') || t.includes('Submit a Proposal'))) {
                btns[i].click();
                return 'Clicked: ' + t;
              }
            }
            return 'Could not click submit';
          })()
        `);
        console.log('Submit:', clicked);
        await sleep(5000);

        // Check result
        const resultUrl = await c.ev('window.location.href');
        const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
        console.log('Result URL:', resultUrl);
        console.log('Result:', resultText.substring(0, 200));

        if (resultText.includes('submitted') || resultText.includes('Proposal') || !resultUrl.includes('apply')) {
          applied++;
          console.log('SUCCESS: Applied!');
        } else {
          failed++;
          console.log('UNCERTAIN: May need manual review');
        }
      }
    } else {
      console.log('SKIP: No textarea found on proposal form');
      failed++;
    }

    await sleep(2000);
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`RESULTS: Applied: ${applied}, Failed: ${failed}, Total attempted: ${targetJobs.length}`);
  console.log(`${'='.repeat(60)}`);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
