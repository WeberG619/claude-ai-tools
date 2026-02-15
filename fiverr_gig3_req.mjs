// Fill gig #3 requirements (wizard=3) and save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Click "+ Add New Question"
  console.log("=== Add Requirement ===");
  let r = await eval_(`
    const addBtn = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .find(el => el.textContent.trim().includes('Add New Question'));
    if (addBtn) {
      addBtn.scrollIntoView({ block: 'center' });
      const rect = addBtn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no add button' });
  `);
  console.log("Add button:", r);
  const addBtn = JSON.parse(r);

  if (!addBtn.error) {
    await clickAt(send, addBtn.x, addBtn.y);
    await sleep(1000);

    // Find the textarea for the question
    r = await eval_(`
      const textarea = document.querySelector('textarea');
      if (textarea) {
        textarea.scrollIntoView({ block: 'center' });
        textarea.focus();
        const rect = textarea.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no textarea' });
    `);
    console.log("Textarea:", r);
    const ta = JSON.parse(r);

    if (!ta.error) {
      await clickAt(send, ta.x, ta.y);
      await sleep(200);
      await send("Input.insertText", { text: "Please provide your current resume (if available), target job title/industry, and any specific achievements or skills you'd like highlighted." });
      await sleep(500);
      console.log("Question typed");

      // Click "Add" button
      r = await eval_(`
        const addSubmit = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Add');
        if (addSubmit) {
          addSubmit.scrollIntoView({ block: 'center' });
          const rect = addSubmit.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no Add button' });
      `);
      console.log("Add submit:", r);
      const addSubmit = JSON.parse(r);

      if (!addSubmit.error) {
        await clickAt(send, addSubmit.x, addSubmit.y);
        await sleep(1000);
        console.log("Requirement added");
      }
    }
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(1000);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(8000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);

    // Navigate forward if stuck
    const state = JSON.parse(r);
    if (state.wizard === '3' && state.errors.length === 0) {
      await eval_(`window.location.href = location.href.replace(/wizard=3/, 'wizard=4').replace(/&tab=\\w+/, '')`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
      console.log("Nav to wizard=4:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
