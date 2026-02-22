// Fix Freelancer profile using exact field IDs
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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

async function clearAndType(send, eval_, elementId, value) {
  // Use the native value setter to clear Angular's tracked value
  await eval_(`
    const el = document.getElementById(${JSON.stringify(elementId)});
    if (!el) return 'not found';
    const nativeSetter = Object.getOwnPropertyDescriptor(
      el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype, 'value'
    ).set;
    nativeSetter.call(el, '');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.focus();
    el.click();
    return 'cleared';
  `);
  await sleep(200);

  // Triple-click to select all (backup clear)
  const r = await eval_(`
    const el = document.getElementById(${JSON.stringify(elementId)});
    const rect = el.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
  `);
  const pos = JSON.parse(r);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(200);

  // Verify it's clear
  const val = await eval_(`document.getElementById(${JSON.stringify(elementId)}).value`);
  if (val && val.length > 0) {
    // Force clear via native setter again
    await eval_(`
      const el = document.getElementById(${JSON.stringify(elementId)});
      const nativeSetter = Object.getOwnPropertyDescriptor(
        el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype, 'value'
      ).set;
      nativeSetter.call(el, '');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    `);
    await sleep(200);
  }

  // Now type the value
  await eval_(`document.getElementById(${JSON.stringify(elementId)}).focus()`);
  await sleep(100);
  await send("Input.insertText", { text: value });
  await sleep(300);

  // Verify
  const result = await eval_(`document.getElementById(${JSON.stringify(elementId)}).value`);
  return result;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // 1. Fix Professional Headline (max 50 chars)
  const headline = "Writer & Data Specialist | AI Tools";  // 35 chars
  console.log(`1. Headline (${headline.length} chars)...`);
  let val = await clearAndType(send, eval_, "professional-headline", headline);
  console.log(`   Value: "${val}" (${val?.length} chars)`);

  // 2. Fix Summary
  const summary = "Data specialist and writer with AI-enhanced tools for fast, accurate delivery.";
  console.log(`\n2. Summary (${summary.length} chars)...`);
  val = await clearAndType(send, eval_, "summary", summary);
  console.log(`   Value: "${val?.substring(0, 50)}..." (${val?.length} chars)`);

  // 3. Hourly Rate
  console.log("\n3. Hourly Rate...");
  val = await clearAndType(send, eval_, "hourly-rate", "35");
  console.log(`   Value: $${val}/hr`);

  // 4. Address - need to use the Google Places autocomplete
  console.log("\n4. Address...");
  // Find the address input
  let r = await eval_(`
    const addrInput = document.querySelector('input[placeholder="Enter your address"]');
    if (addrInput) {
      // Clear it
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(addrInput, '');
      addrInput.dispatchEvent(new Event('input', { bubbles: true }));
      addrInput.focus();
      addrInput.click();
      const rect = addrInput.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    // Click and clear
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
    await sleep(200);

    // Type "Seattle" character by character to trigger Google Places
    await send("Input.insertText", { text: "Seattle" });
    await sleep(2000); // Wait for Google Places autocomplete

    // Click the first Google Places suggestion (.pac-item)
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('.pac-item'))
        .filter(el => el.offsetParent !== null || window.getComputedStyle(el.parentElement).display !== 'none');
      if (items.length > 0) {
        // Click the first item
        items[0].click();
        return 'selected: ' + items[0].textContent.trim().substring(0, 60);
      }
      // Check if pac-container exists
      const container = document.querySelector('.pac-container');
      return container ? 'container exists but no items visible' : 'no pac-container found';
    `);
    console.log("   Autocomplete:", r);

    if (r.includes('no') || r.includes('container exists')) {
      // Try dispatching mouse events on pac-item
      await sleep(500);
      r = await eval_(`
        const container = document.querySelector('.pac-container');
        if (container) {
          const items = container.querySelectorAll('.pac-item');
          if (items.length > 0) {
            const rect = items[0].getBoundingClientRect();
            return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: items[0].textContent.trim().substring(0, 50) });
          }
          return JSON.stringify({ containerDisplay: window.getComputedStyle(container).display, items: items.length });
        }
        return null;
      `);
      console.log("   PAC details:", r);

      if (r && r.includes('"x"')) {
        const pacPos = JSON.parse(r);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pacPos.x, y: pacPos.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pacPos.x, y: pacPos.y, button: "left", clickCount: 1 });
        console.log("   Clicked PAC item:", pacPos.text);
      }
    }
    await sleep(500);
  }

  // Verify address
  r = await eval_(`
    const addrInput = document.querySelector('input[placeholder="Enter your address"]');
    return addrInput?.value || 'empty';
  `);
  console.log("   Address value:", r);

  // 5. Click Save
  console.log("\n5. Saving...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("   Clicked Save");
  }
  await sleep(3000);

  // Check for errors or success
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 100))
      .filter(t => t.length > 5);
    const bidForm = document.querySelector('[class*="PlaceBid"], textarea[placeholder*="bid"], [class*="bid-form"]');
    const bidBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().toLowerCase().includes('place bid') || b.textContent.trim().toLowerCase().includes('bid'));
    return JSON.stringify({
      errors,
      hasBidForm: !!bidForm,
      hasBidBtn: bidBtn ? bidBtn.textContent.trim() : null,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n6. Result:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
