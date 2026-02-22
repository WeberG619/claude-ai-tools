// Fix Freelancer profile using execCommand for Angular compatibility
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
  console.log("Connected\n");

  // Use a completely different approach: click the field, select all via CDP, delete, then insertText
  const fields = [
    { id: "professional-headline", value: "Writer & Data Specialist" },  // 24 chars, well under 50
    { id: "summary", value: "Professional writer and data specialist delivering high-quality content and accurate data processing. I use AI-enhanced tools for fast, precise results across writing, research, and data entry projects." },  // ~200 chars
    { id: "hourly-rate", value: "35" }
  ];

  for (const field of fields) {
    console.log(`\nFilling #${field.id}...`);

    // Click the field to focus it
    let r = await eval_(`
      const el = document.getElementById(${JSON.stringify(field.id)});
      if (!el) return null;
      el.scrollIntoView({ block: 'center' });
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    `);

    if (!r) {
      console.log("  NOT FOUND");
      continue;
    }

    const pos = JSON.parse(r);

    // Click to focus
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(300);

    // Select all with Ctrl+A
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);

    // Delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    // Verify clear
    r = await eval_(`document.getElementById(${JSON.stringify(field.id)}).value`);
    console.log(`  After clear: "${r}" (${r?.length || 0} chars)`);

    // Now use insertText
    await send("Input.insertText", { text: field.value });
    await sleep(300);

    // Tab out to trigger change/blur
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(200);

    // Verify
    r = await eval_(`document.getElementById(${JSON.stringify(field.id)}).value`);
    console.log(`  Final: "${r?.substring(0, 50)}${r?.length > 50 ? '...' : ''}" (${r?.length} chars)`);
  }

  // Address - use Google Places
  console.log("\nFilling address...");
  let r = await eval_(`
    const addrInput = document.querySelector('input[placeholder="Enter your address"]');
    if (!addrInput) return null;
    addrInput.scrollIntoView({ block: 'center' });
    const rect = addrInput.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(300);

    // Select all and delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    // Type "Seattle, WA" slowly to trigger Google Places
    await send("Input.insertText", { text: "Seattle, WA, USA" });
    await sleep(3000);

    // Check for pac-container
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
      // Try arrow down + enter to select first suggestion
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      console.log("  Used ArrowDown + Enter for suggestion");
      await sleep(1000);
    }

    // Check address value
    r = await eval_(`document.querySelector('input[placeholder="Enter your address"]').value`);
    console.log("  Address value:", r);
  }

  // Check all field values before saving
  console.log("\n=== PRE-SAVE CHECK ===");
  r = await eval_(`
    return JSON.stringify({
      firstName: document.getElementById('first-name')?.value,
      lastName: document.getElementById('last-name')?.value,
      headline: document.getElementById('professional-headline')?.value,
      headlineLen: document.getElementById('professional-headline')?.value?.length,
      summary: document.getElementById('summary')?.value?.substring(0, 60),
      summaryLen: document.getElementById('summary')?.value?.length,
      rate: document.getElementById('hourly-rate')?.value,
      address: document.querySelector('input[placeholder="Enter your address"]')?.value
    });
  `);
  console.log(r);

  // Click Save
  console.log("\nSaving...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
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
    console.log("Clicked Save");
  }
  await sleep(4000);

  // Check result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 100));

    // Check if bid section appeared
    const bidSection = document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Bid on this');
    const stillNeedsProfile = document.body.innerText.includes('Complete your profile');

    return JSON.stringify({
      errors,
      bidSection,
      stillNeedsProfile,
      preview: document.body.innerText.substring(0, 1000)
    });
  `);
  console.log("\n=== RESULT ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
