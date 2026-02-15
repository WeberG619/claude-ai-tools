// Upwork profile step 3/10: Skills
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Check current page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: document.body.innerText.substring(0, 400),
      inputs: Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          type: el.type, id: el.id,
          placeholder: (el.placeholder || '').substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }))
    });
  `);
  console.log("Page state:", r);
  const state = JSON.parse(r);

  // Check what skills are already suggested
  r = await eval_(`
    const chips = Array.from(document.querySelectorAll('[class*="chip"], [class*="tag"], [class*="badge"], [class*="pill"], [class*="token"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 2 && el.textContent.trim().length < 40)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(chips);
  `);
  console.log("Existing chips:", r);

  // Find the search input for skills
  const searchInput = state.inputs.find(i => i.type === 'text' || i.type === 'search' || i.placeholder.toLowerCase().includes('skill'));

  if (searchInput) {
    const skills = ["Content Writing", "Proofreading", "Resume Writing", "Data Entry", "Microsoft Excel", "Technical Writing"];

    for (const skill of skills) {
      // Click input
      await clickAt(send, searchInput.x, searchInput.y);
      await sleep(300);

      // Clear any existing text
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
      await sleep(200);

      // Type skill
      await send("Input.insertText", { text: skill });
      await sleep(1500);

      // Find suggestion dropdown
      r = await eval_(`
        const opts = Array.from(document.querySelectorAll('[role="option"], [role="listbox"] li, [class*="suggestion"] li, [class*="dropdown"] li, ul[class*="list"] li'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
          .map(el => ({
            text: el.textContent.trim().substring(0, 50),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(opts.slice(0, 5));
      `);
      const opts = JSON.parse(r);
      console.log(`  "${skill}" suggestions:`, opts.length);

      if (opts.length > 0) {
        // Click the first matching suggestion
        const exact = opts.find(o => o.text.toLowerCase().includes(skill.toLowerCase())) || opts[0];
        await clickAt(send, exact.x, exact.y);
        console.log(`  Added: ${exact.text}`);
        await sleep(500);
      } else {
        // Try pressing Enter
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
        await sleep(500);
        console.log(`  Pressed Enter for: ${skill}`);
      }
    }
  } else {
    console.log("No search input found. Looking for skill buttons to click...");
    // Maybe skills are presented as clickable buttons
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('button, [role="button"], [class*="skill"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3 && el.textContent.trim().length < 40
          && el.getBoundingClientRect().y > 200 && el.getBoundingClientRect().y < 700)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    console.log("Skill buttons:", r);
  }

  // Click Next
  await sleep(1000);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next' });
  `);
  const next = JSON.parse(r);
  if (!next.error) {
    await clickAt(send, next.x, next.y);
    console.log("Clicked Next");
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 300) })`);
    console.log("\nNext page:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
