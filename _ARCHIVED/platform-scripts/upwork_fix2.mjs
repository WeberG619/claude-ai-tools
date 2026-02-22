// Fix Upwork: rate to $50, DOB 03/18/1974, address 619 Hopkins Rd Sandpoint ID 83864
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

async function clearAndType(send, eval_, placeholder, value) {
  // Focus and get position
  const r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === '${placeholder}' && el.offsetParent !== null);
    if (inp) {
      inp.scrollIntoView({ block: 'center' });
      inp.focus();
      // Clear using React setter
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inp, '');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      const rect = inp.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found: ${placeholder}' });
  `);
  const pos = JSON.parse(r);
  if (pos.error) {
    console.log(`  SKIP: ${pos.error}`);
    return false;
  }
  await sleep(200);
  await clickAt(send, pos.x, pos.y);
  await sleep(200);
  // Triple-click to select all
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);
  await send("Input.insertText", { text: value });
  await sleep(300);
  return true;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Check current step
  let r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Current step:", r);

  // Step 1: Go back to fix rate if on location page
  if (r === 'location') {
    console.log("=== Going back to rate page ===");
    await eval_(`
      const btn = document.querySelector('button');
      const back = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Back');
      if (back) back.click();
    `);
    await sleep(3000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
    console.log("Now on:", r);
  }

  // Fix rate to $50
  if (r === 'rate') {
    console.log("=== Setting rate to $50 ===");
    // Clear and set via React setter first
    await eval_(`
      const inp = document.querySelector('input.air3-input:not([disabled])');
      if (inp) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, '');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.scrollIntoView({ block: 'center' });
        inp.focus();
      }
    `);
    await sleep(300);

    r = await eval_(`
      const inp = document.querySelector('input.air3-input:not([disabled])');
      if (inp) {
        const rect = inp.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    const ratePos = JSON.parse(r);
    if (!ratePos.error) {
      await clickAt(send, ratePos.x, ratePos.y);
      await sleep(200);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: ratePos.x, y: ratePos.y, button: "left", clickCount: 3 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ratePos.x, y: ratePos.y, button: "left", clickCount: 3 });
      await sleep(100);
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
      console.log("Rate:", r);
    }

    // Click Next
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null && !b.textContent.includes('Skip to'));
      if (btn) { btn.scrollIntoView({ block: 'center' }); const rect = btn.getBoundingClientRect(); return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) }); }
      return JSON.stringify({ error: 'none' });
    `);
    await sleep(300);
    const next = JSON.parse(r);
    if (!next.error) await clickAt(send, next.x, next.y);
    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // Step 2: Fill location/personal info
  console.log("\n=== Filling personal details ===");

  // DOB: 03/18/1974
  console.log("DOB...");
  await clearAndType(send, eval_, "mm/dd/yyyy", "03/18/1974");
  await sleep(300);
  // Tab out to validate
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
  await sleep(500);

  // Street address: 619 Hopkins Rd
  console.log("Address...");
  await clearAndType(send, eval_, "Enter street address", "619 Hopkins Rd");
  await sleep(1500);
  // Check for autocomplete
  r = await eval_(`
    const opts = Array.from(document.querySelectorAll('[role="option"], [class*="pac-item"], [class*="suggestion"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
      .map(el => ({ text: el.textContent.trim().substring(0, 60), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
    return JSON.stringify(opts);
  `);
  console.log("Address suggestions:", r);
  const addrOpts = JSON.parse(r);
  // Look for Sandpoint match
  const sandpoint = addrOpts.find(o => o.text.includes('Sandpoint') || o.text.includes('Hopkins'));
  if (sandpoint) {
    await clickAt(send, sandpoint.x, sandpoint.y);
    console.log(`Selected: ${sandpoint.text}`);
    await sleep(1000);
  } else if (addrOpts.length > 0) {
    // Try first one
    await clickAt(send, addrOpts[0].x, addrOpts[0].y);
    console.log(`Selected first: ${addrOpts[0].text}`);
    await sleep(1000);
  }

  // Check auto-fill
  r = await eval_(`
    const fields = {};
    Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
      fields[inp.placeholder || inp.type] = inp.value;
    });
    return JSON.stringify(fields);
  `);
  console.log("Fields after address:", r);
  const autoFields = JSON.parse(r);

  // Fill city if not auto-filled
  if (!autoFields['Enter city']) {
    console.log("City...");
    await clearAndType(send, eval_, "Enter city", "Sandpoint");
    await sleep(500);
  }

  // Fill state if not auto-filled
  if (!autoFields['Enter state/province']) {
    console.log("State...");
    await clearAndType(send, eval_, "Enter state/province", "ID");
    await sleep(500);
  }

  // Fill ZIP if not auto-filled
  if (!autoFields['Enter ZIP/Postal code']) {
    console.log("ZIP...");
    await clearAndType(send, eval_, "Enter ZIP/Postal code", "83864");
    await sleep(500);
  }

  // Phone
  if (!autoFields['Enter number']) {
    console.log("Phone...");
    await clearAndType(send, eval_, "Enter number", "2085551234");
    await sleep(500);
  }

  // Final field check
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
  console.log("\nFinal check:", r);

  // Click Review
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) { btn.scrollIntoView({ block: 'center' }); const rect = btn.getBoundingClientRect(); return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) }); }
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

    r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 500) })`);
    const page = JSON.parse(r);
    console.log("\n=== " + page.step + " ===");
    console.log(page.body.substring(0, 350));

    // If review page, submit
    if (page.step !== 'location') {
      // Look for Submit button
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null && !el.textContent.includes('Skip to'))
          .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
        return JSON.stringify(btns);
      `);
      console.log("Buttons:", r);
      const btns = JSON.parse(r);
      const submit = btns.find(b => b.text.includes('Submit') || b.text.includes('Publish') || b.text.includes('Done'));
      if (submit) {
        await clickAt(send, submit.x, submit.y);
        console.log(`Clicked: ${submit.text}`);
        await sleep(8000);
        ws.close(); await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
        console.log("\n*** RESULT:", r);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
