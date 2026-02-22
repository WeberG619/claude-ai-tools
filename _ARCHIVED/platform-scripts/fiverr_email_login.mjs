const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const fiverrTab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (!fiverrTab) { console.log("No Fiverr tab"); return; }

  const ws = new WebSocket(fiverrTab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  const clickAt = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  };

  // Go back to login page
  await send("Page.navigate", { url: "https://www.fiverr.com/login" });
  await sleep(4000);

  // Click "Continue with email/username"
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('email'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Email button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(pos.x, pos.y);
    await sleep(2000);

    // Check for input fields
    r = await eval_(`
      const inputs = document.querySelectorAll('input');
      return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
        type: i.type,
        name: i.name,
        id: i.id,
        placeholder: i.placeholder,
        autocomplete: i.autocomplete
      })));
    `);
    console.log("Inputs:", r);

    // Type email into the email/username field
    r = await eval_(`
      const input = document.querySelector('input[type="text"], input[type="email"], input[name="login"]');
      if (input) {
        const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSet.call(input, 'weberg619');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        return 'typed username';
      }
      return 'no input found';
    `);
    console.log("Username:", r);
    await sleep(500);

    // Look for Continue/Next/Submit button
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null);
      return JSON.stringify(btns.map(b => ({
        text: b.textContent.trim().substring(0, 40),
        type: b.type,
        disabled: b.disabled,
        rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("Buttons:", r);

    // Click Continue button
    const btns = JSON.parse(r);
    const continueBtn = btns.find(b => b.text.includes('Continue') || b.text.includes('Log') || b.text.includes('Sign'));
    if (continueBtn) {
      await clickAt(continueBtn.rect.x, continueBtn.rect.y);
      console.log("Clicked:", continueBtn.text);
      await sleep(3000);

      // Check what's next (password field?)
      r = await eval_(`
        const inputs = document.querySelectorAll('input');
        return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
          type: i.type,
          name: i.name,
          placeholder: i.placeholder
        })));
      `);
      console.log("\nInputs after continue:", r);

      r = await eval_(`return document.body.innerText.substring(0, 1500)`);
      console.log("\nPage:", r);
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
