// Physically type prices and check errors after save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to price area
  await eval_(`window.scrollTo(0, 800)`);
  await sleep(500);

  // Get price input positions
  let r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .slice(0, 3)
      .map(el => ({
        value: el.value,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(priceInputs);
  `);
  console.log("Price inputs:", r);
  const priceInputs = JSON.parse(r);
  const prices = ["10", "25", "50"];

  // Physically click and type each price
  for (let i = 0; i < priceInputs.length; i++) {
    const input = priceInputs[i];
    console.log(`\nPrice ${i}: current="${input.value}", target="${prices[i]}"`);

    // Triple-click to select all
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: input.x, y: input.y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: input.x, y: input.y, button: "left", clickCount: 3 });
    await sleep(200);

    // Type the price
    await send("Input.insertText", { text: prices[i] });
    await sleep(300);

    // Tab out to trigger validation
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(300);
  }

  // Also physically type word counts
  console.log("\n=== Word Counts ===");
  r = await eval_(`
    const wordInputs = Array.from(document.querySelectorAll('input[type="number"]'))
      .filter(el => el.offsetParent !== null && !el.className.includes('price') && !el.className.includes('stepper'))
      .slice(0, 3)
      .map(el => ({
        value: el.value,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(wordInputs);
  `);
  console.log("Word inputs:", r);
  const wordInputs = JSON.parse(r);
  const words = ["1000", "3000", "5000"];

  for (let i = 0; i < wordInputs.length; i++) {
    if (wordInputs[i].value === words[i]) continue;
    console.log(`  Word ${i}: "${wordInputs[i].value}" -> "${words[i]}"`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: wordInputs[i].x, y: wordInputs[i].y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: wordInputs[i].x, y: wordInputs[i].y, button: "left", clickCount: 3 });
    await sleep(200);
    await send("Input.insertText", { text: words[i] });
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(200);
  }

  // Scroll to Save & Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(800);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    console.log(`\nClicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(3000);

    // Immediately check for errors
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [class*="warning"], [role="alert"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
        .map(el => ({
          text: el.textContent.trim().substring(0, 100),
          class: (el.className?.toString() || '').substring(0, 60),
          y: Math.round(el.getBoundingClientRect().y)
        }));

      // Also check for toast/notification messages
      const toasts = Array.from(document.querySelectorAll('[class*="toast"], [class*="notification"], [class*="snackbar"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100));

      return JSON.stringify({ errors, toasts, url: location.href, wizard: new URL(location.href).searchParams.get('wizard') });
    `);
    console.log("\nAfter save:", r);

    await sleep(3000);

    // Check again after more time
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: (document.body?.innerText || '').substring(300, 800)
      });
    `);
    console.log("Final state:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
