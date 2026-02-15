// Upwork rate - focus input via JS, type rate char by char
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

  // Clear any erroneous input from previous attempt
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input.air3-input'))
      .filter(el => el.offsetParent !== null && !el.disabled);
    // Clear all visible inputs first
    inputs.forEach(inp => {
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(inp, '');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    });
    return JSON.stringify(inputs.map(i => ({ val: i.value, ph: i.placeholder })));
  `);
  console.log("Cleared inputs:", r);
  await sleep(500);

  // Focus the first (hourly rate) input via JS and set value
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input.air3-input'))
      .filter(el => el.offsetParent !== null && !el.disabled);
    if (inputs.length > 0) {
      const rateInput = inputs[0];
      rateInput.scrollIntoView({ block: 'center' });
      rateInput.focus();
      rateInput.click();
      return JSON.stringify({
        focused: document.activeElement === rateInput,
        x: Math.round(rateInput.getBoundingClientRect().x + rateInput.getBoundingClientRect().width/2),
        y: Math.round(rateInput.getBoundingClientRect().y + rateInput.getBoundingClientRect().height/2)
      });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("Focused input:", r);
  const focusInfo = JSON.parse(r);
  await sleep(300);

  if (!focusInfo.error) {
    // Click at the input position to ensure CDP focus
    await clickAt(send, focusInfo.x, focusInfo.y);
    await sleep(300);

    // Verify focus
    r = await eval_(`
      const ae = document.activeElement;
      return JSON.stringify({ tag: ae.tagName, class: (ae.className || '').substring(0, 40), type: ae.type || '' });
    `);
    console.log("Active element:", r);

    // Select all and delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    // Type "25" using insertText
    await send("Input.insertText", { text: "25" });
    await sleep(500);

    // Check
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input.air3-input'))
        .filter(el => el.offsetParent !== null);
      return JSON.stringify(inputs.map(i => ({ val: i.value, disabled: i.disabled })));
    `);
    console.log("Values after insertText:", r);

    // Tab to trigger calculation
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(1000);

    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input.air3-input'))
        .filter(el => el.offsetParent !== null);
      return JSON.stringify(inputs.map(i => ({ val: i.value, disabled: i.disabled })));
    `);
    console.log("Values after tab:", r);
  }

  // Check errors
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('rate'))
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify(errors);
  `);
  console.log("Errors:", r);

  // Click Next
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null && !b.textContent.includes('Skip to'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
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
