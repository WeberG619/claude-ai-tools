// Fix mandatory fields and publish Guru service
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
  let { ws, send, eval_ } = await connect();
  console.log("Connected\n");

  // Step 1: Fix title length
  console.log("Step 1: Check and fix title...");
  let r = await eval_(`
    const titleInput = document.querySelector('input[placeholder*="App Development"]');
    if (!titleInput) return "title input not found";
    const maxLen = titleInput.maxLength || titleInput.getAttribute('maxlength');
    const current = titleInput.value;
    return "Current: '" + current + "' (len=" + current.length + ", max=" + maxLen + ")";
  `);
  console.log("  ", r);

  // Shorten title if needed
  r = await eval_(`
    const titleInput = document.querySelector('input[placeholder*="App Development"]');
    if (!titleInput) return "not found";
    // Shorten to fit: "BIM Modeling & Revit Services" = 29 chars
    titleInput.focus();
    titleInput.value = "BIM Modeling & Revit Services";
    titleInput.dispatchEvent(new Event('input', { bubbles: true }));
    titleInput.dispatchEvent(new Event('change', { bubbles: true }));
    return "Title set to: " + titleInput.value + " (len=" + titleInput.value.length + ")";
  `);
  console.log("  ", r);
  await sleep(300);

  // Step 2: Select relevant skills
  console.log("\nStep 2: Select skills...");
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');

    const targetSkills = [
      'Autodesk Revit', 'Building Information Modeling', 'CAD Modeling',
      'Construction', 'Drafting', 'Modeling', 'Artificial Intelligence'
    ];

    let selected = [];
    for (const cb of checkboxes) {
      const lbl = cb.closest('label') || cb.parentElement;
      const text = lbl?.textContent?.trim() || '';
      if (targetSkills.some(s => text.includes(s))) {
        if (!cb.checked) {
          cb.click();
          selected.push(text);
        }
      }
    }
    return "Selected " + selected.length + " skills: " + selected.join(', ');
  `);
  console.log("  ", r);
  await sleep(500);

  // Step 3: Check for any other mandatory fields we might have missed
  console.log("\nStep 3: Check all mandatory/error fields...");
  r = await eval_(`
    // Look for error indicators
    const errorFields = Array.from(document.querySelectorAll('[class*="error"], [class*="mandatory"], [class*="required"], .has-error'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        tag: el.tagName,
        class: el.className.substring(0, 80),
        parentText: el.parentElement?.textContent?.trim()?.substring(0, 100) || ''
      }));

    // Also check for red borders or visual indicators
    const redBorders = Array.from(document.querySelectorAll('input, select, textarea, [contenteditable]'))
      .filter(el => {
        const style = window.getComputedStyle(el);
        return style.borderColor === 'red' || style.borderColor === 'rgb(255, 0, 0)' ||
               el.classList.contains('error') || el.classList.contains('invalid');
      })
      .map(el => ({
        tag: el.tagName, id: el.id, name: el.name,
        placeholder: el.placeholder, value: (el.value || '').substring(0, 30)
      }));

    return JSON.stringify({ errorFields: errorFields.slice(0, 10), redBorders }, null, 2);
  `);
  console.log("  ", r);

  // Step 4: Scroll down to see full form and check for more fields
  console.log("\nStep 4: Check form completeness...");
  r = await eval_(`
    // Get full form layout
    const sections = Array.from(document.querySelectorAll('h3, h4, .section-title, [class*="heading"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());

    // Check the "Service Thumbnail" section
    const thumbnailSection = document.body.innerText.includes('Service Thumbnail');
    const publishBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Publish');

    return JSON.stringify({
      sections,
      hasThumbnail: thumbnailSection,
      hasPublish: !!publishBtn,
      formText: document.body.innerText.substring(0, 2500)
    }, null, 2);
  `);
  // Just show key parts
  const parsed = JSON.parse(r);
  console.log("  Sections:", parsed.sections);
  console.log("  Has thumbnail:", parsed.hasThumbnail);
  console.log("  Has publish:", parsed.hasPublish);

  // Step 5: Try Save instead of Publish (might be less strict)
  console.log("\nStep 5: Click Save...");
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save');
    if (saveBtn) { saveBtn.click(); return "Save clicked"; }
    return "Save not found";
  `);
  console.log("  ", r);
  await sleep(4000);

  // Check result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .alert-danger, [class*="mandatory"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 150));
    const success = Array.from(document.querySelectorAll('[class*="success"], .alert-success'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 150));
    const notification = document.body.innerText.substring(0, 800);
    return JSON.stringify({
      url: location.href,
      errors: [...new Set(errors)].slice(0, 10),
      success,
      notification: notification.includes('saved') || notification.includes('Saved') || notification.includes('success') ? 'SAVED!' : 'check page'
    }, null, 2);
  `);
  console.log("  Result:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
