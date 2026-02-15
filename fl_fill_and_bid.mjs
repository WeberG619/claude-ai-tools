// Fill remaining profile fields on job page and submit bid
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected - on data entry job page\n");

  // Check current field values
  let r = await eval_(`
    return JSON.stringify({
      headline: document.getElementById('professional-headline')?.value,
      headlineLen: document.getElementById('professional-headline')?.value?.length,
      summary: document.getElementById('summary')?.value?.substring(0, 50),
      summaryLen: document.getElementById('summary')?.value?.length,
      rate: document.getElementById('hourly-rate')?.value,
      firstName: document.getElementById('first-name')?.value,
      lastName: document.getElementById('last-name')?.value,
      address: document.querySelector('input[placeholder="Enter your address"]')?.value
    });
  `);
  console.log("Current values:", r);

  const vals = JSON.parse(r);

  // Fill hourly rate if empty
  if (!vals.rate) {
    console.log("\nFilling hourly rate...");
    r = await eval_(`
      const el = document.getElementById('hourly-rate');
      if (!el) return 'NOT FOUND';
      el.focus();
      el.select ? el.select() : document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, '35');
      return 'set to: ' + el.value;
    `);
    console.log("  Rate:", r);
  } else {
    console.log("Rate already set:", vals.rate);
  }

  // Fill address if empty
  if (!vals.address) {
    console.log("\nFilling address...");
    // Click the address field
    r = await eval_(`
      const addrInput = document.querySelector('input[placeholder="Enter your address"]');
      if (!addrInput) return null;
      addrInput.scrollIntoView({ block: 'center' });
      addrInput.focus();
      addrInput.click();
      const rect = addrInput.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    `);

    if (r) {
      const pos = JSON.parse(r);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(300);

      // Type "Seattle, WA" to trigger Google Places
      await send("Input.insertText", { text: "Seattle, WA" });
      console.log("  Typed 'Seattle, WA'");
      await sleep(3000);

      // Check for Google Places suggestions
      r = await eval_(`
        const pacItems = Array.from(document.querySelectorAll('.pac-item'));
        return JSON.stringify({
          count: pacItems.length,
          items: pacItems.slice(0, 3).map(p => ({
            text: p.textContent.trim().substring(0, 60),
            rect: (() => { const r = p.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, h: r.height }; })()
          }))
        });
      `);
      console.log("  PAC items:", r);

      const pacData = JSON.parse(r);
      if (pacData.count > 0 && pacData.items[0].rect.h > 0) {
        const p = pacData.items[0].rect;
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1 });
        console.log("  Selected:", pacData.items[0].text);
        await sleep(1000);
      } else {
        // Try ArrowDown + Enter
        console.log("  No visible PAC items, trying ArrowDown+Enter...");
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
        await sleep(1000);
      }

      // Check address value
      r = await eval_(`document.querySelector('input[placeholder="Enter your address"]').value`);
      console.log("  Address value:", r);
    }
  } else {
    console.log("Address already set:", vals.address);
  }

  // Verify all fields before saving
  await sleep(500);
  r = await eval_(`
    return JSON.stringify({
      firstName: document.getElementById('first-name')?.value,
      lastName: document.getElementById('last-name')?.value,
      headline: document.getElementById('professional-headline')?.value,
      headlineLen: document.getElementById('professional-headline')?.value?.length,
      summaryLen: document.getElementById('summary')?.value?.length,
      rate: document.getElementById('hourly-rate')?.value,
      address: document.querySelector('input[placeholder="Enter your address"]')?.value
    });
  `);
  console.log("\n=== PRE-SAVE VALUES ===");
  console.log(r);

  // Click Save
  console.log("\nClicking Save...");
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (saveBtn) {
      saveBtn.scrollIntoView({ block: 'center' });
      const rect = saveBtn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("Clicked Save");
    await sleep(5000);
  }

  // Check result after saving
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error" i], [class*="Error" i], [class*="validation" i]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 120));

    const completeProfile = document.body.innerText.includes('Complete your profile');
    const placeBid = document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Place Bid');
    const bidAmount = document.body.innerText.includes('Bid Amount') || document.body.innerText.includes('Your bid');
    const bidTextarea = Array.from(document.querySelectorAll('textarea'))
      .filter(t => t.offsetParent !== null)
      .map(t => ({ id: t.id, placeholder: t.placeholder?.substring(0, 50) }));

    return JSON.stringify({
      url: location.href,
      errors: [...new Set(errors)],
      completeProfile,
      placeBid,
      bidAmount,
      bidTextareas: bidTextarea,
      preview: document.body.innerText.substring(0, 3000)
    });
  `);
  console.log("\n=== AFTER SAVE ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
