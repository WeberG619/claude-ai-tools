// Fix Upwork DOB field and rate, then submit
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

  // Step 1: Go back to rate page
  console.log("=== Fix Rate: Going back ===");
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Back' && b.offsetParent !== null);
    if (btn) { btn.click(); return 'back clicked'; }
    return 'no back';
  `);
  console.log(r);
  await sleep(3000);
  ws.close(); await sleep(500);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Step:", r);

  if (r === 'rate') {
    // Clear using React setter then type
    await eval_(`
      const inp = document.querySelector('input.air3-input:not([disabled])');
      if (inp) {
        inp.scrollIntoView({ block: 'center' });
        inp.focus();
        // Use React setter to clear
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, '');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
    `);
    await sleep(300);

    r = await eval_(`
      const inp = document.querySelector('input.air3-input:not([disabled])');
      if (inp) {
        const rect = inp.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: inp.value });
      }
      return JSON.stringify({ error: 'none' });
    `);
    console.log("Rate input:", r);
    const pos = JSON.parse(r);

    if (!pos.error) {
      await clickAt(send, pos.x, pos.y);
      await sleep(200);
      // Triple click to select all
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
      await sleep(200);
      await send("Input.insertText", { text: "50" });
      await sleep(300);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
      await sleep(500);

      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input.air3-input'))
          .filter(el => el.offsetParent !== null);
        return JSON.stringify(inputs.map(i => ({ val: i.value, disabled: i.disabled })));
      `);
      console.log("Rate values:", r);
    }

    // Click Next to go back to location
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
    }
    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // Step 2: Fix DOB on location page
  console.log("\n=== Fix DOB ===");
  r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Step:", r);

  // Clear DOB using React setter
  await eval_(`
    const dobInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'mm/dd/yyyy' && el.offsetParent !== null);
    if (dobInput) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(dobInput, '');
      dobInput.dispatchEvent(new Event('input', { bubbles: true }));
      dobInput.dispatchEvent(new Event('change', { bubbles: true }));
      dobInput.scrollIntoView({ block: 'center' });
      dobInput.focus();
    }
  `);
  await sleep(300);

  r = await eval_(`
    const dobInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'mm/dd/yyyy' && el.offsetParent !== null);
    if (dobInput) {
      const rect = dobInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: dobInput.value });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("DOB input:", r);
  const dobPos = JSON.parse(r);

  if (!dobPos.error) {
    await clickAt(send, dobPos.x, dobPos.y);
    await sleep(200);
    // Triple click to select all
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: dobPos.x, y: dobPos.y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: dobPos.x, y: dobPos.y, button: "left", clickCount: 3 });
    await sleep(200);
    // Delete selected
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(100);
    // Type DOB
    await send("Input.insertText", { text: "01/15/1990" });
    await sleep(500);

    // Tab out
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(500);

    r = await eval_(`
      const dobInput = Array.from(document.querySelectorAll('input'))
        .find(el => el.placeholder === 'mm/dd/yyyy' && el.offsetParent !== null);
      return dobInput ? dobInput.value : 'none';
    `);
    console.log("DOB value:", r);
  }

  // Verify all fields
  r = await eval_(`
    const fields = {};
    Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
      fields[inp.placeholder || inp.type] = inp.value;
    });
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify({ fields, errors });
  `);
  console.log("\nAll fields:", r);

  // Click Review
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
  const reviewBtn = JSON.parse(r);
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked Review");
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href,
      step: location.href.split('/').pop().split('?')[0],
      body: document.body.innerText.substring(0, 600)
    })`);
    const page = JSON.parse(r);
    console.log("\n=== Page: " + page.step + " ===");
    console.log(page.body.substring(0, 400));

    // If on review page, submit
    if (page.body.includes('looks great') || page.body.includes('review') || page.step === 'review' || page.body.includes('Submit')) {
      // Find submit button
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null && !el.textContent.includes('Skip to'))
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(btns);
      `);
      console.log("Buttons:", r);
      const btns = JSON.parse(r);
      const submit = btns.find(b => b.text.includes('Submit') || b.text.includes('Publish') || b.text.includes('Done'));
      if (submit) {
        await clickAt(send, submit.x, submit.y);
        console.log(`\nClicked: ${submit.text}`);
        await sleep(8000);
        ws.close(); await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
        console.log("\n*** FINAL:", r);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
