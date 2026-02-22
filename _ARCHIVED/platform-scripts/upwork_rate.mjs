// Upwork rate page - handle formatted currency input
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

  // Debug: get all inputs and their details
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        type: el.type, id: el.id, name: el.name || '',
        value: el.value, placeholder: el.placeholder || '',
        class: (el.className || '').substring(0, 80),
        label: (el.labels && el.labels[0]) ? el.labels[0].textContent.trim().substring(0, 50) : '',
        ariaLabel: el.getAttribute('aria-label') || '',
        readonly: el.readOnly,
        disabled: el.disabled,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(inputs);
  `);
  console.log("All inputs:", r);
  const inputs = JSON.parse(r);

  // Find the editable rate input (first non-readonly one or labeled "hourly rate")
  const rateInput = inputs.find(i => !i.readonly && !i.disabled && i.type === 'text');

  if (rateInput) {
    console.log(`Rate input: id=${rateInput.id}, value="${rateInput.value}", label="${rateInput.label}"`);

    // Scroll into view
    await eval_(`
      const inp = document.querySelector('input[type="text"]:not([readonly]):not([disabled])');
      if (inp) inp.scrollIntoView({ block: 'center' });
    `);
    await sleep(300);

    // Re-get position
    r = await eval_(`
      const inp = document.querySelector('input[type="text"]:not([readonly]):not([disabled])');
      if (inp) {
        const rect = inp.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    const pos = JSON.parse(r);

    // Triple-click to select all text in the input
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: pos.x, y: pos.y });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
    await sleep(200);

    // Type the rate
    await send("Input.insertText", { text: "25" });
    await sleep(500);

    // Check value
    r = await eval_(`
      const inp = document.querySelector('input[type="text"]:not([readonly]):not([disabled])');
      return inp ? inp.value : 'none';
    `);
    console.log("Rate value after typing:", r);

    // If still $0.00, try different approach
    if (r === '$0.00' || r === '0.00' || r === '') {
      console.log("Rate not set, trying keyboard approach...");
      await clickAt(send, pos.x, pos.y);
      await sleep(200);

      // Use Home key to go to start, then type
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Home", code: "Home" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Home", code: "Home" });
      await sleep(100);

      // Select all with Ctrl+A
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(100);

      // Delete
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
      await sleep(100);

      // Type character by character
      for (const char of "25.00") {
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, code: `Key${char.toUpperCase()}` });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: char, code: `Key${char.toUpperCase()}` });
        await sleep(50);
      }

      await sleep(500);
      r = await eval_(`
        const inp = document.querySelector('input[type="text"]:not([readonly]):not([disabled])');
        return inp ? inp.value : 'none';
      `);
      console.log("Rate after keyboard:", r);
    }

    // If STILL not set, try using nativeInputValueSetter
    if (r === '$0.00' || r === '0.00' || r === '') {
      console.log("Trying React value setter approach...");
      await eval_(`
        const inp = document.querySelector('input[type="text"]:not([readonly]):not([disabled])');
        if (inp) {
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          nativeInputValueSetter.call(inp, '25.00');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
        }
      `);
      await sleep(500);
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input[type="text"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.value);
        return JSON.stringify(inputs);
      `);
      console.log("All input values after React setter:", r);
    }
  }

  // Tab away to trigger validation/calculation
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
  await sleep(1000);

  // Check final state
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ value: el.value, label: el.getAttribute('aria-label') || '', readonly: el.readOnly }));
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify({ inputs, errors });
  `);
  console.log("Final state:", r);

  // Try clicking Next
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
