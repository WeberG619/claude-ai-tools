// Fill Guru.com service form via CDP - all evals wrapped in IIFEs
const CDP_HTTP = "http://localhost:9222";

async function getGuruTab() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru.com tab found!");
  return guru;
}

async function connectTab(tab) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener("open", () => {
      const send = (method, params = {}) => {
        return new Promise((res, rej) => {
          const msgId = id++;
          pending.set(msgId, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id: msgId, method, params }));
        });
      };
      resolve({ ws, send });
    });
    ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) p.reject(new Error(msg.error.message));
        else p.resolve(msg.result);
      }
    });
    ws.addEventListener("error", () => reject(new Error("WebSocket error")));
  });
}

async function evaluate(send, expression) {
  // Always wrap in IIFE to avoid scope pollution
  const wrapped = `(() => { ${expression} })()`;
  const result = await send("Runtime.evaluate", {
    expression: wrapped,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) {
    throw new Error(JSON.stringify(result.exceptionDetails));
  }
  return result.result?.value;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const tab = await getGuruTab();
  const { ws, send } = await connectTab(tab);
  console.log("Connected to Guru tab:", tab.title);

  try {
    // Reload page to clear any stale state
    console.log("Reloading page...");
    await send("Page.reload", { ignoreCache: false });
    await sleep(3000);

    // Make sure "Add a Service" radio is selected
    console.log("Selecting 'Add a Service'...");
    let r = await evaluate(send, `
      const radio = document.getElementById('radioSvc');
      if (radio) { radio.click(); return "clicked"; }
      return "not found";
    `);
    console.log("  Radio:", r);
    await sleep(1500);

    // Fill Service Title
    console.log("Filling Service Title...");
    r = await evaluate(send, `
      const input = document.querySelector('input[placeholder="E.g. Android App Development"]');
      if (!input) return "title input not found";
      input.focus();
      input.value = "BIM Modeling & Revit Drafting Services";
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return "title set";
    `);
    console.log("  Title:", r);
    await sleep(500);

    // Fill Service Description
    console.log("Filling Service Description...");
    r = await evaluate(send, `
      const editor = document.querySelector('.fr-element.fr-view')
        || document.querySelector('[contenteditable="true"]');
      if (!editor) return "editor not found";
      editor.focus();
      editor.innerHTML = '<p><strong>BIM Ops Studio</strong> delivers professional BIM modeling, Revit drafting, and construction documentation services for architects, engineers, and contractors.</p>' +
        '<p><strong>Services Include:</strong></p>' +
        '<ul>' +
        '<li>Revit 3D modeling from sketches, PDFs, or CAD drawings</li>' +
        '<li>Construction document sets (floor plans, elevations, sections, details)</li>' +
        '<li>BIM coordination and clash detection</li>' +
        '<li>As-built documentation and existing conditions modeling</li>' +
        '<li>Revit family creation (custom components and parametric families)</li>' +
        '<li>PDF-to-Revit and CAD-to-Revit conversion</li>' +
        '<li>Technical writing and specifications</li>' +
        '</ul>' +
        '<p><strong>Why Choose Us:</strong></p>' +
        '<ul>' +
        '<li>Fast turnaround with efficient workflows</li>' +
        '<li>Experienced in residential, commercial, and healthcare projects</li>' +
        '<li>Proficient in Revit 2024/2025/2026, AutoCAD, and Bluebeam</li>' +
        '<li>Clear communication and organized deliverables</li>' +
        '</ul>' +
        '<p>Contact us to discuss your project and get a custom quote.</p>';
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      return "description set (" + editor.innerHTML.length + " chars)";
    `);
    console.log("  Description:", r);
    await sleep(500);

    // Select category: Engineering & Architecture
    console.log("Selecting category...");
    r = await evaluate(send, `
      const btns = Array.from(document.querySelectorAll('button, input[type="submit"]'));
      const eng = btns.find(b => (b.textContent || b.value || '').includes("Engineering & Architecture"));
      if (!eng) return "Engineering category not found. Available: " + btns.map(b => (b.textContent||b.value||'').trim()).filter(t=>t.length>3).join(', ');
      eng.scrollIntoView({ behavior: 'smooth', block: 'center' });
      eng.click();
      return "clicked Engineering & Architecture";
    `);
    console.log("  Category:", r);
    await sleep(2000);

    // Check for subcategories/skills
    console.log("Checking skills...");
    r = await evaluate(send, `
      const items = Array.from(document.querySelectorAll('input[type="checkbox"], .skill-item, [class*="skill"], [class*="category"]'))
        .filter(el => el.offsetParent !== null && el.id !== 'ProfileVisibility');
      const labels = items.map(el => {
        if (el.type === 'checkbox') {
          const lbl = el.closest('label') || document.querySelector('label[for="'+el.id+'"]');
          return { type: 'checkbox', id: el.id, text: lbl?.textContent?.trim() || '', checked: el.checked };
        }
        return { type: el.tagName, text: el.textContent?.trim()?.substring(0,50) };
      });
      return JSON.stringify(labels.slice(0, 25));
    `);
    console.log("  Skills:", r);

    // Check for cost section
    console.log("Checking cost section...");
    r = await evaluate(send, `
      window.scrollTo(0, document.body.scrollHeight);
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, id: i.id, placeholder: i.placeholder, value: i.value }));
      const selects = Array.from(document.querySelectorAll('select'))
        .filter(s => s.offsetParent !== null)
        .map(s => ({ id: s.id, name: s.name, options: Array.from(s.options).slice(0,10).map(o => o.text) }));
      return JSON.stringify({ inputs, selects });
    `);
    console.log("  Cost:", r);

    // Take screenshot equivalent - get page HTML summary
    console.log("\nDone filling form. Check browser to verify, then scroll down to see category/cost sections.");

  } finally {
    ws.close();
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
