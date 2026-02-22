// Click Engineering & Architecture on Guru.com - handle any button type
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

  // Find ALL buttons and list them
  console.log("Listing all buttons on page...");
  let r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    return JSON.stringify(btns.map(b => ({
      type: b.type,
      text: b.textContent.trim().substring(0, 50),
      classes: b.className.substring(0, 80),
      visible: b.offsetParent !== null
    })).filter(b => b.visible && b.text.length > 2));
  `);
  console.log("Visible buttons:", r);

  // Now find and click Engineering & Architecture
  console.log("\nClicking Engineering & Architecture...");
  r = await eval_(`
    const allBtns = Array.from(document.querySelectorAll('button'));
    const eng = allBtns.find(b => b.textContent.trim().includes("Engineering & Architecture"));
    if (!eng) return "not found among " + allBtns.length + " buttons";

    // Intercept form submission
    const form = eng.closest('form');
    if (form) {
      const origSubmit = form.submit;
      form.addEventListener('submit', (e) => { e.preventDefault(); e.stopPropagation(); }, { once: true });
    }

    // Also change button type temporarily
    const origType = eng.type;
    eng.type = "button";
    eng.click();

    return "clicked (was type=" + origType + ")";
  `);
  console.log("  Result:", r);
  await sleep(3000);

  // Screenshot state - check what appeared
  r = await eval_(`
    // Check if skills/subcategories appeared
    const newCheckboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');
    const newBtns = Array.from(document.querySelectorAll('.skill-chip, .tag, .badge, [class*="skill-"], [class*="subcat"]'));
    const activeClass = Array.from(document.querySelectorAll('.active, .selected, [class*="active"], [class*="selected"]'))
      .map(el => ({ tag: el.tagName, text: el.textContent.trim().substring(0, 30), class: el.className.substring(0, 50) }));

    // Did any modal or dropdown appear?
    const modals = Array.from(document.querySelectorAll('.modal, [class*="modal"], [class*="popup"], [class*="overlay"]'))
      .filter(m => m.offsetParent !== null);

    // Check full page state around the category section
    const catSection = document.querySelector('[class*="category"], [class*="Category"]');

    return JSON.stringify({
      newCheckboxes: newCheckboxes.length,
      newSkillElements: newBtns.length,
      activeElements: activeClass.slice(0, 5),
      modalCount: modals.length,
      titleValue: document.querySelector('input[placeholder*="App Development"]')?.value || 'not found',
      editorContent: (document.querySelector('.fr-element')?.innerHTML || '').substring(0, 100)
    }, null, 2);
  `);
  console.log("State after click:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
