// Upwork profile 10/10: Fill personal details and submit
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

async function focusAndType(send, eval_, placeholder, value) {
  // Focus input by placeholder
  const r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === '${placeholder}' && el.offsetParent !== null);
    if (inp) {
      inp.scrollIntoView({ block: 'center' });
      inp.focus();
      inp.click();
      const rect = inp.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const pos = JSON.parse(r);
  if (pos.error) {
    console.log(`  Input "${placeholder}" not found`);
    return false;
  }

  await sleep(200);
  await clickAt(send, pos.x, pos.y);
  await sleep(200);

  // Select all and clear
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
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

  // First, go back to rate page to change rate to $50
  console.log("=== Going back to change rate to $50 ===");
  let r = await eval_(`
    const backBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Back' && b.offsetParent !== null);
    if (backBtn) {
      backBtn.click();
      return 'clicked back';
    }
    return 'no back button';
  `);
  console.log(r);
  await sleep(3000);
  ws.close(); await sleep(500);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Current step:", r);

  if (r === 'rate') {
    // Update rate to $50
    await eval_(`
      const inp = document.querySelector('input.air3-input:not([disabled])');
      if (inp) { inp.scrollIntoView({ block: 'center' }); inp.focus(); }
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
    const pos = JSON.parse(r);
    if (!pos.error) {
      await clickAt(send, pos.x, pos.y);
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(50);
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

    // Click Next to go back to location page
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
    }
    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  console.log("\n=== Filling personal details ===");

  // Date of Birth
  console.log("Setting DOB...");
  const dobSet = await focusAndType(send, eval_, "mm/dd/yyyy", "01/15/1990");
  console.log("DOB:", dobSet ? "set" : "failed");
  await sleep(500);

  // Street address
  console.log("Setting address...");
  const addrSet = await focusAndType(send, eval_, "Enter street address", "1234 Sunset Blvd");
  await sleep(1500);
  // Click first autocomplete if available
  r = await eval_(`
    const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="dropdown"] li, [class*="pac-item"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
      .map(el => ({
        text: el.textContent.trim().substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(opts);
  `);
  console.log("Address suggestions:", r);
  const addrOpts = JSON.parse(r);
  if (addrOpts.length > 0) {
    await clickAt(send, addrOpts[0].x, addrOpts[0].y);
    console.log(`Selected: ${addrOpts[0].text}`);
    await sleep(1000);
  }

  // Check if city/state/zip auto-filled from address selection
  r = await eval_(`
    const fields = {};
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null);
    for (const inp of inputs) {
      if (inp.placeholder === 'Enter city') fields.city = inp.value;
      if (inp.placeholder === 'Enter state/province') fields.state = inp.value;
      if (inp.placeholder === 'Enter ZIP/Postal code') fields.zip = inp.value;
      if (inp.placeholder === 'Enter number') fields.phone = inp.value;
    }
    return JSON.stringify(fields);
  `);
  console.log("Auto-filled fields:", r);
  const autoFilled = JSON.parse(r);

  // Fill city if empty
  if (!autoFilled.city) {
    console.log("Setting city...");
    await focusAndType(send, eval_, "Enter city", "Los Angeles");
    await sleep(1000);
    // Check for autocomplete
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    const cityOpts = JSON.parse(r);
    if (cityOpts.length > 0) {
      await clickAt(send, cityOpts[0].x, cityOpts[0].y);
      console.log(`City: ${cityOpts[0].text}`);
    }
    await sleep(500);
  }

  // Fill state if empty
  if (!autoFilled.state) {
    console.log("Setting state...");
    await focusAndType(send, eval_, "Enter state/province", "California");
    await sleep(500);
  }

  // Fill zip if empty
  if (!autoFilled.zip) {
    console.log("Setting ZIP...");
    await focusAndType(send, eval_, "Enter ZIP/Postal code", "90028");
    await sleep(500);
  }

  // Fill phone if empty
  if (!autoFilled.phone) {
    console.log("Setting phone...");
    await focusAndType(send, eval_, "Enter number", "3105551234");
    await sleep(500);
  }

  // Check for date picker - might need to use the "Choose date" button
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ ph: el.placeholder, val: el.value }));
    return JSON.stringify(inputs);
  `);
  console.log("\nAll field values:", r);

  // Check for errors
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify(errors);
  `);
  console.log("Errors:", r);

  // Click Review your profile
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent.trim().substring(0, 40) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
  const reviewBtn = JSON.parse(r);
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log(`Clicked: ${reviewBtn.text}`);
    await sleep(5000);

    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href,
      step: location.href.split('/').pop().split('?')[0],
      body: document.body.innerText.substring(0, 500)
    })`);
    const nextPage = JSON.parse(r);
    console.log("\n=== Next page: " + nextPage.step + " ===");
    console.log(nextPage.body.substring(0, 300));

    // If review page, click Submit
    if (nextPage.step === 'review' || nextPage.body.includes('review') || nextPage.body.includes('looks great') || nextPage.body.includes('Submit')) {
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => (b.textContent.trim().includes('Submit') || b.textContent.trim().includes('Publish'))
            && b.offsetParent !== null && !b.textContent.includes('Skip to'));
        if (btn) {
          btn.scrollIntoView({ block: 'center' });
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent.trim().substring(0, 40) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      await sleep(300);
      const submitBtn = JSON.parse(r);
      if (!submitBtn.error) {
        await clickAt(send, submitBtn.x, submitBtn.y);
        console.log(`\nClicked: ${submitBtn.text}`);
        await sleep(5000);
        ws.close(); await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 400) })`);
        console.log("\n*** FINAL:", r);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
