// Fix pricing - delivery times, revisions, and other missing fields
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

  // Check for validation errors
  let r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [class*="warning"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        class: (el.className?.toString() || '').substring(0, 60)
      }));
    return JSON.stringify(errors);
  `);
  console.log("Errors:", r);

  // Look at the delivery time and revisions "dropdowns" - they're likely custom components
  r = await eval_(`
    // Find delivery time row
    const deliveryRow = Array.from(document.querySelectorAll('tr, [class*="row"]'))
      .find(el => el.textContent?.includes('DELIVERY TIME'));
    if (deliveryRow) {
      // Find all clickable elements in the delivery row
      const clickables = Array.from(deliveryRow.querySelectorAll('button, [role="button"], [class*="select"], [class*="dropdown"], [class*="picker"], td'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 30),
          class: (el.className?.toString() || '').substring(0, 60),
          role: el.getAttribute('role') || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify({ found: true, clickables });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("Delivery row:", r);

  // Find DELIVERY TIME text in individual cells to click them
  r = await eval_(`
    const cells = Array.from(document.querySelectorAll('td'))
      .filter(el => el.textContent.includes('DELIVERY TIME') && el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(cells);
  `);
  console.log("Delivery time cells:", r);
  const deliveryCells = JSON.parse(r);

  // Click each delivery time cell and select option
  for (let i = 0; i < deliveryCells.length; i++) {
    const cell = deliveryCells[i];
    console.log(`\nClicking delivery time cell ${i} at (${cell.x}, ${cell.y})`);
    await clickAt(send, cell.x, cell.y);
    await sleep(800);

    // Check for dropdown/popup
    r = await eval_(`
      const popup = document.querySelector('[class*="popup"], [class*="dropdown-menu"], [class*="menu-list"], [class*="options"], [role="listbox"]');
      if (popup && popup.offsetParent) {
        const items = Array.from(popup.querySelectorAll('[class*="option"], li, [role="option"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify({ open: true, items });
      }
      return JSON.stringify({ open: false });
    `);
    console.log("Dropdown:", r);
    const dd = JSON.parse(r);

    if (dd.open && dd.items.length > 0) {
      // For Basic: 3 days, Standard: 2 days, Premium: 1 day
      const dayTargets = ["3 day", "2 day", "1 day"];
      const target = dayTargets[i] || "3 day";
      const match = dd.items.find(item => item.text.includes(target)) || dd.items[0];
      console.log(`Selecting: "${match.text}"`);
      await clickAt(send, match.x, match.y);
      await sleep(500);
    }
  }

  // Handle Revisions SELECT cells
  console.log("\n=== Setting Revisions ===");
  r = await eval_(`
    const revCells = Array.from(document.querySelectorAll('td'))
      .filter(el => {
        const t = el.textContent.trim();
        return (t === 'SELECT' || t.includes('SELECT')) && el.offsetParent !== null;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(revCells);
  `);
  console.log("Revision SELECT cells:", r);
  const revCells = JSON.parse(r);

  for (let i = 0; i < revCells.length; i++) {
    console.log(`\nClicking revision cell ${i} at (${revCells[i].x}, ${revCells[i].y})`);
    await clickAt(send, revCells[i].x, revCells[i].y);
    await sleep(800);

    r = await eval_(`
      const popup = document.querySelector('[class*="popup"], [class*="dropdown-menu"], [class*="menu-list"], [role="listbox"]');
      if (popup && popup.offsetParent) {
        const items = Array.from(popup.querySelectorAll('[class*="option"], li, [role="option"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify({ open: true, items });
      }
      return JSON.stringify({ open: false });
    `);
    console.log("Dropdown:", r);
    const dd = JSON.parse(r);

    if (dd.open) {
      // Select Unlimited or highest revision option
      const match = dd.items.find(item => item.text.includes('Unlimited')) ||
                    dd.items.find(item => item.text.includes('3')) ||
                    dd.items[dd.items.length - 1];
      if (match) {
        console.log(`Selecting: "${match.text}"`);
        await clickAt(send, match.x, match.y);
        await sleep(500);
      }
    }
  }

  // Verify prices are set
  console.log("\n=== Verifying Prices ===");
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ value: el.value, x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
    return JSON.stringify(priceInputs);
  `);
  console.log("Prices:", r);
  const prices = JSON.parse(r);

  // Set prices if empty
  const priceValues = ["10", "25", "50"];
  for (let i = 0; i < Math.min(prices.length, priceValues.length); i++) {
    if (!prices[i].value || prices[i].value === "0") {
      console.log(`Setting price ${i} to $${priceValues[i]}`);
      await clickAt(send, prices[i].x, prices[i].y);
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(100);
      await send("Input.insertText", { text: priceValues[i] });
      await sleep(300);
      // Click elsewhere to commit
      await clickAt(send, 300, 500);
      await sleep(200);
    }
  }

  // Check all errors again
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\nRemaining errors:", r);

  // Scroll to and try Save & Continue
  console.log("\n=== Saving ===");
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
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 600)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
