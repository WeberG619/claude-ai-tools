// Create 2nd Fiverr gig - Writing & Proofreading - Overview step
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs/new"));
  if (!tab) throw new Error(`Page not found: manage_gigs/new`);
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("manage_gigs/new");
  console.log("Connected to new gig page\n");

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 2000)
    });
  `);
  let state = JSON.parse(r);
  console.log("URL:", state.url);

  if (state.isError) {
    console.log("Bot detection. Exiting.");
    ws.close();
    return;
  }

  console.log("Body:", state.body.substring(0, 500));

  // Check form fields
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 60),
        value: (el.value || '').substring(0, 60),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(inputs);
  `);
  console.log("\nForm fields:", r);

  // Fill in the gig title
  // Writing & Proofreading gig
  const gigTitle = "I will do professional proofreading, editing, and rewriting of your content";

  console.log("\n=== Filling Title ===");
  r = await eval_(`
    const titleInput = document.querySelector('input[name="title"], input[placeholder*="do"], textarea[name="title"]');
    if (titleInput) {
      titleInput.focus();
      titleInput.value = '';
      const rect = titleInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), found: true });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("Title input:", r);
  const titleInput = JSON.parse(r);

  if (titleInput.found) {
    await clickAt(send, titleInput.x, titleInput.y);
    await sleep(300);
    // Clear and type
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    await send("Input.insertText", { text: gigTitle });
    await sleep(500);
    console.log("Title filled:", gigTitle);
  }

  // Select category: Writing & Translation > Proofreading & Editing
  console.log("\n=== Selecting Category ===");
  r = await eval_(`
    const selects = Array.from(document.querySelectorAll('select, [class*="select"], [class*="dropdown"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        name: el.name || '',
        id: el.id || '',
        class: (el.className?.toString() || '').substring(0, 60),
        options: el.tagName === 'SELECT' ? Array.from(el.options).map(o => o.textContent.trim().substring(0, 40)).slice(0, 10) : [],
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2)
      }));
    return JSON.stringify(selects);
  `);
  console.log("Dropdowns:", r);

  // Look for category select
  const selects = JSON.parse(r);
  const catSelect = selects.find(s => s.name.includes('category') || s.name.includes('cat') || s.id.includes('category'));
  if (catSelect) {
    console.log(`Found category dropdown: ${catSelect.name || catSelect.id}`);
    // Select "Writing & Translation"
    r = await eval_(`
      const sel = document.querySelector('select[name="${catSelect.name}"], #${catSelect.id}');
      if (sel) {
        const opt = Array.from(sel.options).find(o => o.textContent.includes('Writing'));
        if (opt) {
          sel.value = opt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Selected: ' + opt.textContent.trim();
        }
      }
      return 'not found';
    `);
    console.log("Category:", r);
    await sleep(2000);
  }

  // Check for subcategory
  r = await eval_(`
    const selects2 = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name || '',
        id: el.id || '',
        options: Array.from(el.options).map(o => ({ text: o.textContent.trim().substring(0, 50), val: o.value })).slice(0, 20),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(selects2);
  `);
  console.log("\nAll selects after category:", r);

  // Check for the subcategory with Proofreading
  r = await eval_(`
    const allSelects = Array.from(document.querySelectorAll('select')).filter(el => el.offsetParent !== null);
    for (const sel of allSelects) {
      const opt = Array.from(sel.options).find(o => o.textContent.includes('Proofreading') || o.textContent.includes('Editing'));
      if (opt) {
        sel.value = opt.value;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Selected subcategory: ' + opt.textContent.trim() + ' (from ' + sel.name + ')';
      }
    }
    return 'no proofreading option found';
  `);
  console.log("Subcategory:", r);
  await sleep(2000);

  // Check for sub-subcategory
  r = await eval_(`
    const allSelects = Array.from(document.querySelectorAll('select')).filter(el => el.offsetParent !== null);
    const result = allSelects.map(sel => ({
      name: sel.name,
      options: Array.from(sel.options).map(o => o.textContent.trim().substring(0, 50)).slice(0, 15)
    }));
    return JSON.stringify(result);
  `);
  console.log("All select options now:", r);

  // Check page state and look for Save & Continue
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        disabled: el.disabled
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify(btns);
  `);
  console.log("\nButtons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
