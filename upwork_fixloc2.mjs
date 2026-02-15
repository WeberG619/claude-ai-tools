// Navigate back to location step, fix city, then re-submit
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

async function clearAndTypeField(send, eval_, placeholder, value) {
  const r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === '${placeholder}' && el.offsetParent !== null);
    if (inp) {
      inp.scrollIntoView({ block: 'center' });
      inp.focus();
      inp.click();
      const rect = inp.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: inp.value });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const pos = JSON.parse(r);
  if (pos.error) {
    console.log(`  ${placeholder}: NOT FOUND`);
    return false;
  }

  console.log(`  ${placeholder}: current="${pos.val}"`);
  
  if (pos.val === value) {
    console.log(`  → already correct`);
    return true;
  }
  
  await sleep(200);
  await clickAt(send, pos.x, pos.y);
  await sleep(200);

  // Select all
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(100);

  // Delete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);

  // Type
  await send("Input.insertText", { text: value });
  await sleep(300);

  // Escape autocomplete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(200);

  // Tab out
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
  await sleep(300);

  // Verify
  const v = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === '${placeholder}' && el.offsetParent !== null);
    return inp ? inp.value : 'not found';
  `);
  console.log(`  → now: "${v}"`);
  return v === value;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Navigate to location step
  console.log("Navigating to location step...");
  await eval_(`window.location.href = 'https://www.upwork.com/nx/create-profile/location'`);
  await sleep(4000);

  // Reconnect after navigation
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  console.log("Reconnected\n");

  // Check page
  let r = await eval_(`return JSON.stringify({
    url: location.href,
    inputs: Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ placeholder: el.placeholder || '', value: el.value, type: el.type }))
  })`);
  console.log("Page state:", r);
  const state = JSON.parse(r);

  if (!state.url.includes('location')) {
    console.log("Not on location page. URL:", state.url);
    ws.close();
    return;
  }

  // Fix the fields
  console.log("\n=== Fixing location fields with keyboard input ===\n");

  // Street address first
  await clearAndTypeField(send, eval_, "Enter street address", "619 Hopkins Rd");
  await sleep(500);
  // Dismiss autocomplete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(300);

  // City - the critical fix
  await clearAndTypeField(send, eval_, "Enter city", "Sandpoint");
  await sleep(500);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(300);

  // State
  await clearAndTypeField(send, eval_, "Enter state/province", "ID");
  await sleep(300);

  // ZIP
  await clearAndTypeField(send, eval_, "Enter ZIP/Postal code", "83864");
  await sleep(300);

  // Phone
  await clearAndTypeField(send, eval_, "Enter number", "7865879726");
  await sleep(300);

  // Verify all
  r = await eval_(`
    const fields = {};
    Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
      if (inp.placeholder && inp.placeholder !== '-') fields[inp.placeholder] = inp.value;
    });
    return JSON.stringify(fields, null, 2);
  `);
  console.log("\nAll fields after fix:", r);

  // Click "Review your profile"
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("Review button:", r);
  const reviewBtn = JSON.parse(r);
  
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked Review");
    await sleep(5000);

    // Check for verification dialog or new page
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href,
      hasSandpoint: document.body.innerText.includes('Sandpoint'),
      hasBuffalo: document.body.innerText.includes('Buffalo'),
      hasVerify: document.body.innerText.includes('verify your phone'),
      bodySnippet: document.body.innerText.substring(0, 600)
    })`);
    console.log("\nAfter Review:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
