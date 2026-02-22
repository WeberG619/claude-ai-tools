// Fill Fiverr join page - connect to the actual page tab (not iframes)
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  // Filter for actual pages only, not iframes/workers
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found matching: ${urlMatch}`);
  console.log("Connecting to:", tab.title, "-", tab.url.substring(0, 80));
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
  let { ws, send, eval_ } = await connectToPage("fiverr.com/join");
  console.log("Connected\n");

  // Inspect the page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 3000),
      forms: Array.from(document.querySelectorAll('form')).map(f => ({
        id: f.id, action: f.action, inputs: Array.from(f.querySelectorAll('input, select')).map(i => ({
          tag: i.tagName, type: i.type, name: i.name, id: i.id, placeholder: i.placeholder
        }))
      })),
      allInputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({
          tag: i.tagName, type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder, ariaLabel: i.getAttribute('aria-label')
        }))
    });
  `);
  console.log("Page state:", r);

  const state = JSON.parse(r);

  // Check if there's an email field or "continue with email" button
  if (state.preview.includes("Continue with email") || state.preview.includes("continue with email")) {
    console.log("\nNeed to click 'Continue with email' first...");
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, a'))
        .filter(b => b.offsetParent !== null && b.textContent.toLowerCase().includes('email'));
      if (btns.length > 0) {
        const rect = btns[0].getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btns[0].textContent.trim() });
      }
      return null;
    `);
    if (r) {
      const pos = JSON.parse(r);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      console.log("  Clicked:", pos.text);
      await sleep(2000);

      // Re-check inputs
      r = await eval_(`
        return JSON.stringify(
          Array.from(document.querySelectorAll('input'))
            .filter(i => i.offsetParent !== null)
            .map(i => ({ type: i.type, name: i.name, id: i.id, placeholder: i.placeholder, ariaLabel: i.getAttribute('aria-label') }))
        );
      `);
      console.log("  Inputs after click:", r);
    }
  }

  // Fill email
  console.log("\nFilling email...");
  await eval_(`
    const email = document.querySelector('input[type="email"], input[name="email"], input[name*="email"]');
    if (email) { email.focus(); email.click(); }
    return email ? 'focused email' : 'email not found';
  `);
  await sleep(200);
  // Select all + delete to clear
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(100);
  await send("Input.insertText", { text: "weberg619@gmail.com" });
  await sleep(500);

  // Check for password field and fill it
  r = await eval_(`
    const pass = document.querySelector('input[type="password"]');
    return pass ? 'found' : 'not found';
  `);
  console.log("  Password field:", r);

  if (r === 'found') {
    await eval_(`
      const pass = document.querySelector('input[type="password"]');
      if (pass) { pass.focus(); pass.click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: process.argv[2] || "" });
    console.log("  Entered password");
    await sleep(300);
  }

  // Check for username field
  r = await eval_(`
    const user = document.querySelector('input[name="username"], input[name*="user"], input[placeholder*="username"]');
    return user ? JSON.stringify({ name: user.name, placeholder: user.placeholder }) : 'not found';
  `);
  console.log("  Username field:", r);

  if (r !== 'not found') {
    await eval_(`
      const user = document.querySelector('input[name="username"], input[name*="user"], input[placeholder*="username"]');
      if (user) { user.focus(); user.click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: "bimopsstudio" });
    console.log("  Entered username");
    await sleep(300);
  }

  // Get final state and available buttons
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, name: i.name, value: i.type !== 'password' ? i.value : '***', placeholder: i.placeholder })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({
          text: b.textContent.trim().substring(0, 50),
          type: b.type,
          disabled: b.disabled
        }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("\n=== Final State ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
