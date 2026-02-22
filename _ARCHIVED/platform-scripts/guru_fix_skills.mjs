// Fix Guru skills by clicking them via their IDs and re-select Architecture
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

  // Step 1: Check if Architecture type needs re-selection
  console.log("Step 1: Check/fix Architecture type...");
  let r = await eval_(`
    // The "Architecture" radio might be in the category section
    // Find it and check it
    const allRadios = Array.from(document.querySelectorAll('input[type="radio"]'));
    const results = allRadios.map(r => {
      const lbl = r.closest('label') || r.parentElement;
      return { id: r.id, name: r.name, text: lbl?.textContent?.trim(), checked: r.checked };
    });
    return JSON.stringify(results);
  `);
  console.log("  Radios:", r);

  // Step 2: Click each skill checkbox by ID using dispatchEvent
  console.log("\nStep 2: Check skills by ID...");
  const skillIds = ['skill_0', 'skill_1', 'skill_2', 'skill_3', 'skill_4', 'skill_6', 'skill_8'];
  // skill_0=AI, skill_1=Revit, skill_2=BIM, skill_3=CAD, skill_4=Construction, skill_6=Drafting, skill_8=Modeling

  for (const skillId of skillIds) {
    r = await eval_(`
      const cb = document.getElementById('${skillId}');
      if (!cb) return '${skillId}: not found';
      if (!cb.checked) {
        // Try multiple click methods
        cb.checked = true;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
        cb.dispatchEvent(new Event('click', { bubbles: true }));
        // Also try clicking the label
        const lbl = document.querySelector('label[for="${skillId}"]') || cb.closest('label');
        if (lbl) lbl.click();
      }
      const lbl = cb.closest('label') || cb.parentElement;
      return '${skillId}: ' + (cb.checked ? 'CHECKED' : 'unchecked') + ' - ' + lbl?.textContent?.trim();
    `);
    console.log("  ", r);
    await sleep(200);
  }

  // Step 3: Verify all skills are checked
  console.log("\nStep 3: Verify skills...");
  r = await eval_(`
    const skills = ['skill_0','skill_1','skill_2','skill_3','skill_4','skill_6','skill_8'];
    const states = skills.map(id => {
      const cb = document.getElementById(id);
      const lbl = cb?.closest('label') || cb?.parentElement;
      return { id, checked: cb?.checked, text: lbl?.textContent?.trim() };
    });
    const checkedCount = states.filter(s => s.checked).length;
    return JSON.stringify({ checkedCount, states });
  `);
  console.log("  ", r);

  // Step 4: Try Save again
  console.log("\nStep 4: Save...");
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save');
    if (saveBtn) { saveBtn.click(); return 'Save clicked'; }
    return 'Save not found';
  `);
  console.log("  ", r);
  await sleep(4000);

  // Step 5: Check result
  console.log("\nStep 5: Result...");
  r = await eval_(`
    const bodyText = document.body.innerText.substring(0, 1000);
    const hasError = bodyText.includes('Mandatory') || bodyText.includes('empty') || bodyText.includes('select at least');
    const hasSuccess = bodyText.includes('saved') || bodyText.includes('published') || bodyText.includes('Success');
    return JSON.stringify({
      hasError,
      hasSuccess,
      preview: bodyText.substring(0, 500)
    }, null, 2);
  `);
  console.log("  ", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
