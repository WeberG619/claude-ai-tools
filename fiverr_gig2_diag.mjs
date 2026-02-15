// Diagnose what's preventing Save & Continue on pricing step
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // 1. Check all input fields and their values
  let r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type,
        name: el.name || '',
        class: (el.className?.toString() || '').substring(0, 50),
        value: (el.value || '').substring(0, 30),
        placeholder: (el.placeholder || '').substring(0, 30),
        checked: el.checked,
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(allInputs);
  `);
  console.log("=== All Visible Inputs ===");
  const inputs = JSON.parse(r);
  inputs.forEach((inp, i) => {
    console.log(`  ${i}: ${inp.tag} type=${inp.type} name="${inp.name}" class="${inp.class}" val="${inp.value}" checked=${inp.checked} y=${inp.y}`);
  });

  // 2. Check for any validation errors or required fields
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [class*="required"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        class: (el.className?.toString() || '').substring(0, 60),
        tag: el.tagName
      }));
    return JSON.stringify(errors);
  `);
  console.log("\n=== Errors/Required ===");
  JSON.parse(r).forEach(e => console.log(`  ${e.tag} class="${e.class}" text="${e.text}"`));

  // 3. Check the "Words included" row specifically
  r = await eval_(`
    const wordsRow = Array.from(document.querySelectorAll('tr, [class*="row"]'))
      .filter(el => el.textContent.includes('Words included'))
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent.trim().substring(0, 200),
        inputs: Array.from(el.querySelectorAll('input')).map(i => ({ type: i.type, value: i.value, name: i.name }))
      }));
    return JSON.stringify(wordsRow);
  `);
  console.log("\n=== Words Row ===");
  console.log(r);

  // 4. Check checkboxes (Grammar, Fact checking, AI detection)
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => {
        const label = el.closest('label')?.textContent?.trim()?.substring(0, 40) ||
                      el.parentElement?.textContent?.trim()?.substring(0, 40) || '';
        const row = el.closest('tr, [class*="row"]');
        const rowLabel = row ? Array.from(row.querySelectorAll('td, th, [class*="label"]'))[0]?.textContent?.trim()?.substring(0, 30) || '' : '';
        return {
          name: el.name,
          checked: el.checked,
          label,
          rowLabel,
          y: Math.round(el.getBoundingClientRect().y)
        };
      });
    return JSON.stringify(checkboxes);
  `);
  console.log("\n=== Checkboxes ===");
  JSON.parse(r).forEach(c => console.log(`  name="${c.name}" checked=${c.checked} label="${c.label}" row="${c.rowLabel}" y=${c.y}`));

  // 5. Check revision dropdowns
  r = await eval_(`
    const revs = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && !el.className.includes('duration'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(revs);
  `);
  console.log("\n=== Revisions ===");
  console.log(r);

  // 6. Check the Save button and if it's disabled
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (saveBtn) {
      return JSON.stringify({
        disabled: saveBtn.disabled,
        class: saveBtn.className?.substring(0, 80),
        ariaDisabled: saveBtn.getAttribute('aria-disabled'),
        styles: window.getComputedStyle(saveBtn).opacity + ' ' + window.getComputedStyle(saveBtn).pointerEvents
      });
    }
    return 'no button';
  `);
  console.log("\n=== Save Button ===");
  console.log(r);

  // 7. Get full body text to look for clues
  r = await eval_(`
    return (document.body?.innerText || '').substring(0, 3000);
  `);
  console.log("\n=== Full Body (first 3000 chars) ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
