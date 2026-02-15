// Fix city from Buffalo to Sandpoint using actual keyboard input
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
  // Scroll to field and focus
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
  if (pos.error) return false;

  console.log(`  ${placeholder}: current="${pos.val}"`);
  await sleep(200);

  // Click to focus
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

  // Type new value
  await send("Input.insertText", { text: value });
  await sleep(300);

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
  return true;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Close any open dialog first
  await eval_(`
    const closeBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Close the dialog');
    if (closeBtn) closeBtn.click();
  `);
  await sleep(1000);

  // Fix all fields using actual keyboard input (not React setter)
  console.log("=== Fixing fields with keyboard input ===");

  // Street address
  await clearAndTypeField(send, eval_, "Enter street address", "619 Hopkins Rd");
  await sleep(500);
  // Dismiss any autocomplete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(300);

  // City - this is the critical fix
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
  let r = await eval_(`
    const fields = {};
    Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
      if (inp.placeholder && inp.placeholder !== '-') fields[inp.placeholder] = inp.value;
    });
    return JSON.stringify(fields);
  `);
  console.log("\nAll fields:", r);

  // Click Review
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review your profile') && b.offsetParent !== null);
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
    console.log("\nClicked Review");
    await sleep(3000);

    // Check for verification dialog
    r = await eval_(`
      const hasVerify = document.body.innerText.includes('verify your phone');
      const sendBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Send code' && b.offsetParent !== null);
      const phoneInputs = Array.from(document.querySelectorAll('input[type="tel"]'))
        .filter(el => el.offsetParent !== null);
      return JSON.stringify({ hasVerify, hasSendCode: !!sendBtn, phones: phoneInputs.map(el => el.value) });
    `);
    console.log("After Review:", r);
    const state = JSON.parse(r);

    if (state.hasVerify && state.hasSendCode) {
      // Set phone in dialog and send code
      r = await eval_(`
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        const phoneInputs = Array.from(document.querySelectorAll('input[type="tel"]'))
          .filter(el => el.offsetParent !== null);
        const dialogPhone = phoneInputs[phoneInputs.length - 1];
        if (dialogPhone && dialogPhone.value !== '786 587 9726' && dialogPhone.value !== '7865879726') {
          setter.call(dialogPhone, '7865879726');
          dialogPhone.dispatchEvent(new Event('input', { bubbles: true }));
          dialogPhone.dispatchEvent(new Event('change', { bubbles: true }));
        }
        return phoneInputs.map(el => el.value).join(' | ');
      `);
      console.log("Dialog phones:", r);

      // Click Send code
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Send code' && b.offsetParent !== null);
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      const sendBtn = JSON.parse(r);
      if (!sendBtn.error) {
        await clickAt(send, sendBtn.x, sendBtn.y);
        console.log("Clicked Send code!");
        await sleep(5000);

        r = await eval_(`
          return document.body.innerText.substring(0, 600);
        `);
        console.log("\nPage after send:", r.substring(0, 400));
      }
    }
  }

  ws.close();
  console.log("\n*** Check phone 786-587-9726 for verification code ***");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
