// Fix extras - fill in additional words prices and uncheck extra fast delivery, then save
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

  // Scroll to the extras section
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(500);

  // Fill "Additional words" price-stepper inputs (3 inputs with class price-stepper)
  // These are at y:642, 698, 753 - set $5 each
  console.log("=== Filling Additional Words Prices ===");
  let r = await eval_(`
    const steppers = Array.from(document.querySelectorAll('input.price-stepper'))
      .filter(el => el.offsetParent !== null);
    return JSON.stringify(steppers.map(el => ({
      value: el.value,
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
      class: (el.className?.toString() || '').substring(0, 60)
    })));
  `);
  console.log("Price steppers:", r);
  const steppers = JSON.parse(r);

  // First 3 are "Additional words" prices, next 3 are "Extra fast delivery" prices
  // Fill first 3 with $5 each
  for (let i = 0; i < Math.min(3, steppers.length); i++) {
    if (steppers[i].value) {
      console.log(`  Stepper ${i}: already has value "${steppers[i].value}"`);
      continue;
    }
    console.log(`  Filling stepper ${i} at (${steppers[i].x}, ${steppers[i].y}) with "5"`);
    // Triple-click to select
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: steppers[i].x, y: steppers[i].y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: steppers[i].x, y: steppers[i].y, button: "left", clickCount: 3 });
    await sleep(200);
    await send("Input.insertText", { text: "5" });
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(300);
  }

  // Now handle "Extra fast delivery" - need to uncheck it since it has SELECT dropdowns
  // that are complex. Find the checkbox and uncheck it.
  console.log("\n=== Unchecking Extra Fast Delivery ===");
  r = await eval_(`
    // Find the "Extra fast delivery" section heading/label
    const labels = Array.from(document.querySelectorAll('label, [class*="extra-title"], [class*="toggle"]'));
    const extraFast = labels.find(el => el.textContent.includes('Extra fast delivery'));
    if (extraFast) {
      const checkbox = extraFast.querySelector('input[type="checkbox"]') || extraFast.closest('[class*="extra"]')?.querySelector('input[type="checkbox"]');
      if (checkbox) {
        return JSON.stringify({
          checked: checkbox.checked,
          x: Math.round(checkbox.getBoundingClientRect().x + 10),
          y: Math.round(checkbox.getBoundingClientRect().y + 10)
        });
      }
      // Look for nearby checkbox
      const rect = extraFast.getBoundingClientRect();
      return JSON.stringify({ text: extraFast.textContent.trim().substring(0, 40), x: Math.round(rect.x), y: Math.round(rect.y), noCheckbox: true });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Extra fast delivery:", r);

  // Try to find the extra fast delivery toggle by position
  r = await eval_(`
    // Get all checked checkboxes that are part of the extras section (below the main pricing table)
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 500)
      .map(el => {
        const parent = el.closest('[class*="extra"], [class*="toggle"], label');
        const nearbyText = (parent || el.parentElement)?.textContent?.trim()?.substring(0, 50) || '';
        return {
          checked: el.checked,
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + 10),
          text: nearbyText
        };
      });
    return JSON.stringify(checkboxes);
  `);
  console.log("Extras checkboxes:", r);
  const extraCheckboxes = JSON.parse(r);

  // Find the "Extra fast delivery" one and uncheck if checked
  const fastDelivery = extraCheckboxes.find(c => c.text.includes('Extra fast delivery') || c.text.includes('fast'));
  if (fastDelivery && fastDelivery.checked) {
    console.log(`Unchecking Extra fast delivery at (${fastDelivery.x}, ${fastDelivery.y})`);
    await clickAt(send, fastDelivery.x, fastDelivery.y);
    await sleep(500);
  } else if (fastDelivery) {
    console.log("Extra fast delivery already unchecked");
  }

  // Actually, let's also check if the steppers for fast delivery need filling
  // If fast delivery is still checked, we need to fill those fields too
  // Let's re-check state
  await sleep(500);
  r = await eval_(`
    const steppers = Array.from(document.querySelectorAll('input.price-stepper'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        value: el.value,
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(steppers);
  `);
  console.log("\nRemaining empty steppers:", r);
  const remaining = JSON.parse(r).filter(s => !s.value);

  if (remaining.length > 0) {
    console.log(`Still ${remaining.length} empty stepper fields`);
    // Fill remaining with $10 each
    r = await eval_(`
      const emptySteppers = Array.from(document.querySelectorAll('input.price-stepper'))
        .filter(el => el.offsetParent !== null && !el.value)
        .map(el => ({
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(emptySteppers);
    `);
    const emptySteps = JSON.parse(r);
    for (let i = 0; i < emptySteps.length; i++) {
      console.log(`  Filling empty stepper at (${emptySteps[i].x}, ${emptySteps[i].y})`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: emptySteps[i].x, y: emptySteps[i].y, button: "left", clickCount: 3 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: emptySteps[i].x, y: emptySteps[i].y, button: "left", clickCount: 3 });
      await sleep(200);
      await send("Input.insertText", { text: "10" });
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
      await sleep(300);
    }
  }

  // Check for any SELECT dropdowns that need values
  r = await eval_(`
    const selects = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 500 && el.textContent.trim() === 'SELECT';
      })
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(selects);
  `);
  console.log("\nEmpty SELECT dropdowns:", r);
  const emptySelects = JSON.parse(r);

  // If there are empty selects in extras, we need to either fill them or uncheck the parent extra
  if (emptySelects.length > 0) {
    console.log("Found empty SELECT dropdowns in extras - need to uncheck parent extras");
    // Find and uncheck any checked extras that have empty SELECTs
    r = await eval_(`
      // Find all extra sections with their checkboxes
      const extras = Array.from(document.querySelectorAll('[class*="extra-toggle"], [class*="gig-extra"]'));
      const info = [];

      // Simpler approach - just find checkboxes in the extras area
      const allCbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 500 && el.checked;
        })
        .map(el => ({
          y: Math.round(el.getBoundingClientRect().y),
          x: Math.round(el.getBoundingClientRect().x + 10),
          text: (el.closest('label') || el.parentElement)?.textContent?.trim()?.substring(0, 50)
        }));
      return JSON.stringify(allCbs);
    `);
    console.log("Checked extras:", r);
    const checkedExtras = JSON.parse(r);

    // Uncheck "Extra fast delivery" if still checked
    for (const extra of checkedExtras) {
      if (extra.text && extra.text.includes('fast')) {
        console.log(`Unchecking "${extra.text}" at (${extra.x}, ${extra.y})`);
        await clickAt(send, extra.x, extra.y);
        await sleep(500);
      }
    }
  }

  // Final check - any empty required fields?
  r = await eval_(`
    const emptySteppers = Array.from(document.querySelectorAll('input.price-stepper'))
      .filter(el => el.offsetParent !== null && !el.value).length;
    const emptySelects = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && el.textContent.trim() === 'SELECT' && el.getBoundingClientRect().y > 500).length;
    return JSON.stringify({ emptySteppers, emptySelects });
  `);
  console.log("\nFinal empty fields:", r);

  // Scroll to save and click
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
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors,
        body: (document.body?.innerText || '').substring(200, 800)
      });
    `);
    console.log("\nAfter save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
