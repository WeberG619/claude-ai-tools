// Fill Guru.com service form - correct order:
// 1. Click category (triggers postback)
// 2. Wait for reload
// 3. Fill title, description, rate
// 4. Select skills
// 5. Save/Publish

const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru tab");

  const ws = new WebSocket(guru.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });

  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });

  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });

  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  return { ws, send, eval_ };
}

async function main() {
  console.log("=== Guru.com Profile Builder v3 ===\n");

  // Step 1: Connect and select "Add a Service"
  let { ws, send, eval_ } = await connect();
  console.log("Step 1: Selecting Add a Service...");

  await eval_(`
    const radio = document.getElementById('radioSvc');
    if (radio) radio.click();
    return "done";
  `);
  await sleep(1500);

  // Step 2: Click "Engineering & Architecture" category (will cause postback)
  console.log("Step 2: Clicking Engineering & Architecture category...");
  await eval_(`
    const btns = Array.from(document.querySelectorAll('button[type="submit"]'));
    const eng = btns.find(b => b.textContent.includes("Engineering & Architecture"));
    if (eng) { eng.click(); return "clicked"; }
    return "not found";
  `);

  // Wait for postback to complete
  console.log("  Waiting for postback...");
  await sleep(5000);

  // Reconnect after postback (WebSocket may have closed)
  ws.close();
  ({ ws, send, eval_ } = await connect());
  console.log("  Reconnected after postback");

  // Step 3: Check what's on the page now (should have skills for Engineering)
  console.log("\nStep 3: Checking post-category page state...");
  let r = await eval_(`
    const bodyText = document.body.innerText;
    const hasSkills = bodyText.includes('skill') || bodyText.includes('Skill');
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');

    // Check for title input
    const titleInput = document.querySelector('input[placeholder*="App Development"], input.g-input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])');
    const editor = document.querySelector('.fr-element.fr-view, [contenteditable="true"]');
    const rateInputs = document.querySelectorAll('.rateHourInput__minmax--input');

    // Get any visible labels/text related to skills
    const skillLabels = checkboxes.map(c => {
      const lbl = c.closest('label') || c.parentElement;
      return lbl?.textContent?.trim() || c.name || c.id;
    });

    return JSON.stringify({
      hasTitle: !!titleInput,
      hasEditor: !!editor,
      rateInputCount: rateInputs.length,
      checkboxCount: checkboxes.length,
      skillLabels: skillLabels.slice(0, 30),
      pagePreview: bodyText.substring(0, 800)
    }, null, 2);
  `);
  console.log("  State:", r);

  // Step 4: Fill in Service Title
  console.log("\nStep 4: Filling Service Title...");
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input[type="text"].g-input'));
    const titleInput = inputs.find(i => i.placeholder.includes("App Development") || i.placeholder.includes("E.g."));
    if (!titleInput) {
      // Try broader search
      const allText = inputs.filter(i => !i.className.includes('currency') && !i.className.includes('Search'));
      if (allText.length > 0) {
        allText[0].focus();
        allText[0].value = "BIM Modeling & Revit Drafting Services";
        allText[0].dispatchEvent(new Event('input', { bubbles: true }));
        allText[0].dispatchEvent(new Event('change', { bubbles: true }));
        return "title set (broad match)";
      }
      return "title input not found";
    }
    titleInput.focus();
    titleInput.value = "BIM Modeling & Revit Drafting Services";
    titleInput.dispatchEvent(new Event('input', { bubbles: true }));
    titleInput.dispatchEvent(new Event('change', { bubbles: true }));
    return "title set";
  `);
  console.log("  Result:", r);
  await sleep(300);

  // Step 5: Fill Service Description
  console.log("\nStep 5: Filling Description...");
  r = await eval_(`
    const editor = document.querySelector('.fr-element.fr-view')
      || document.querySelector('[contenteditable="true"]');
    if (!editor) return "editor not found";
    editor.focus();
    editor.innerHTML =
      '<p><strong>BIM Ops Studio</strong> provides professional BIM modeling, Revit drafting, and construction documentation for architects, engineers, and contractors.</p>' +
      '<p><strong>What We Offer:</strong></p>' +
      '<ul>' +
      '<li>Revit 3D modeling from sketches, PDFs, or CAD files</li>' +
      '<li>Full construction document sets (plans, elevations, sections, details)</li>' +
      '<li>BIM coordination and clash detection</li>' +
      '<li>As-built documentation and existing conditions modeling</li>' +
      '<li>Custom Revit family creation and parametric components</li>' +
      '<li>PDF-to-Revit and CAD-to-Revit conversion</li>' +
      '<li>Technical writing, specifications, and reports</li>' +
      '</ul>' +
      '<p><strong>Tools & Expertise:</strong> Revit 2024-2026, AutoCAD, Bluebeam, Navisworks. Experienced in residential, commercial, and healthcare projects.</p>' +
      '<p><strong>AI-Enhanced Workflow:</strong> We leverage AI tools and automation to accelerate production, improve accuracy, and deliver faster turnaround times without sacrificing quality.</p>' +
      '<p>Self-taught professional with hands-on project experience and a portfolio of real delivered work. Clear communication, organized deliverables, and results that speak for themselves.</p>';
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    return "description set";
  `);
  console.log("  Result:", r);
  await sleep(300);

  // Step 6: Fill hourly rate (min and max)
  console.log("\nStep 6: Setting hourly rate...");
  r = await eval_(`
    const rateInputs = Array.from(document.querySelectorAll('.rateHourInput__minmax--input'));
    if (rateInputs.length >= 2) {
      // Min rate
      rateInputs[0].focus();
      rateInputs[0].value = "45";
      rateInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
      rateInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
      // Max rate
      rateInputs[1].focus();
      rateInputs[1].value = "95";
      rateInputs[1].dispatchEvent(new Event('input', { bubbles: true }));
      rateInputs[1].dispatchEvent(new Event('change', { bubbles: true }));
      return "rates set: $45 - $95/hr";
    }
    return "rate inputs not found (found " + rateInputs.length + ")";
  `);
  console.log("  Result:", r);
  await sleep(300);

  // Step 7: Check for and select relevant skills
  console.log("\nStep 7: Selecting skills...");
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');
    if (checkboxes.length === 0) return "no skill checkboxes found";

    const targetSkills = ['revit', 'bim', 'autocad', 'cad', 'architecture', 'drafting', 'modeling',
      '3d', 'construction', 'design', 'engineering', 'documentation', 'technical'];
    let selected = [];

    for (const cb of checkboxes) {
      const lbl = cb.closest('label') || cb.parentElement;
      const text = (lbl?.textContent || cb.name || cb.id || '').toLowerCase();
      if (targetSkills.some(s => text.includes(s))) {
        if (!cb.checked) cb.click();
        selected.push(text.trim().substring(0, 40));
      }
    }
    return "Selected " + selected.length + " skills: " + selected.join(', ');
  `);
  console.log("  Result:", r);

  // Step 8: Look for Save/Publish button
  console.log("\nStep 8: Looking for Save/Publish...");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="button"], a.btn'));
    const actionBtns = btns.filter(b => {
      const text = (b.textContent || b.value || '').toLowerCase();
      return text.includes('save') || text.includes('publish') || text.includes('submit');
    }).map(b => ({
      tag: b.tagName, type: b.type, id: b.id,
      text: (b.textContent || b.value || '').trim(),
      classes: b.className.substring(0, 80)
    }));
    return JSON.stringify(actionBtns);
  `);
  console.log("  Buttons:", r);

  ws.close();
  console.log("\n=== Done ===");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
