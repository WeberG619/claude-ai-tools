// Click Edit near location, fix city from Buffalo to Sandpoint
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

  // Select all with Ctrl+A
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

  // Escape any autocomplete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(200);

  // Tab out to trigger validation
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

  // Step 1: Click the Edit button closest to "Buffalo, ID" location text
  // The Edit button near the name/location area is at (613, 606)
  console.log("Clicking Edit button near location...");
  await clickAt(send, 613, 606);
  await sleep(2000);

  // Check what opened
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ placeholder: el.placeholder || '', value: el.value, type: el.type }));
    const bodySnippet = document.body.innerText.substring(0, 500);
    return JSON.stringify({ inputs, bodySnippet: bodySnippet.substring(0, 300) });
  `);
  console.log("After first Edit click:", r);
  const state1 = JSON.parse(r);

  // Check if we got location inputs (city, state, ZIP)
  const hasCityInput = state1.inputs.some(i => i.placeholder.includes('city'));
  const hasAddressInput = state1.inputs.some(i => i.placeholder.includes('address') || i.placeholder.includes('street'));

  if (!hasCityInput && !hasAddressInput) {
    console.log("\nFirst Edit button wasn't for location. Checking what it opened...");
    
    // Maybe it opened title edit - close it and try another button
    // Press Escape to close any open dialog/form
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
    await sleep(1000);

    // Try the edit button on the right side at (1068, 417) which may be for profile info
    console.log("Trying Edit button at (1068, 417)...");
    await clickAt(send, 1068, 417);
    await sleep(2000);

    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({ placeholder: el.placeholder || '', value: el.value, type: el.type }));
      return JSON.stringify(inputs);
    `);
    console.log("After second Edit click:", r);
    const state2 = JSON.parse(r);
    
    const hasCityNow = state2.some(i => i.placeholder.includes('city'));
    if (!hasCityNow) {
      // Close and try yet another
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
      await sleep(1000);

      // Try scrolling up and looking for location-specific edit
      console.log("Trying to find location edit by examining nearby elements...");
      r = await eval_(`
        // Find "Buffalo" text and look for nearby edit buttons
        const buffaloEl = Array.from(document.querySelectorAll('span'))
          .find(el => el.textContent.includes('Buffalo'));
        if (!buffaloEl) return JSON.stringify({ error: 'no Buffalo text' });
        
        // Walk up to find a section container
        let container = buffaloEl;
        for (let i = 0; i < 10; i++) {
          container = container.parentElement;
          if (!container) break;
          const editBtn = container.querySelector('button[aria-label="Edit"]');
          if (editBtn) {
            const rect = editBtn.getBoundingClientRect();
            return JSON.stringify({ 
              found: true, 
              x: Math.round(rect.x + rect.width/2), 
              y: Math.round(rect.y + rect.height/2),
              containerTag: container.tagName,
              containerClass: (container.className || '').substring(0, 50)
            });
          }
        }
        return JSON.stringify({ error: 'no edit button in location section' });
      `);
      console.log("Location edit search:", r);
      const locEdit = JSON.parse(r);
      if (locEdit.found) {
        await clickAt(send, locEdit.x, locEdit.y);
        await sleep(2000);
        r = await eval_(`
          const inputs = Array.from(document.querySelectorAll('input'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({ placeholder: el.placeholder || '', value: el.value, type: el.type }));
          return JSON.stringify(inputs);
        `);
        console.log("After location Edit click:", r);
      }
    }
  }

  // Now fix the fields if we have them
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ placeholder: el.placeholder || '', value: el.value, type: el.type }));
    return JSON.stringify(inputs);
  `);
  console.log("\nCurrent visible inputs:", r);
  const currentInputs = JSON.parse(r);

  const cityInput = currentInputs.find(i => i.placeholder.includes('city'));
  if (cityInput) {
    console.log("\n=== Fixing location fields ===");
    
    // Fix city
    await clearAndTypeField(send, eval_, "Enter city", "Sandpoint");
    await sleep(500);
    
    // Fix state if needed
    await clearAndTypeField(send, eval_, "Enter state/province", "ID");
    await sleep(300);
    
    // Fix ZIP if needed  
    await clearAndTypeField(send, eval_, "Enter ZIP/Postal code", "83864");
    await sleep(300);
    
    // Fix street if needed
    await clearAndTypeField(send, eval_, "Enter street address", "619 Hopkins Rd");
    await sleep(500);
    // Dismiss autocomplete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
    await sleep(300);
    
    // Verify all fields
    r = await eval_(`
      const fields = {};
      Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
        if (inp.placeholder && inp.placeholder !== '-') fields[inp.placeholder] = inp.value;
      });
      return JSON.stringify(fields);
    `);
    console.log("\nAll fields after fix:", r);

    // Find and click Save/Done button
    await sleep(500);
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(btns);
    `);
    console.log("Buttons:", r);
    const btns = JSON.parse(r);
    const saveBtn = btns.find(b => b.text.includes('Save') || b.text.includes('Done') || b.text.includes('Update'));
    if (saveBtn) {
      await clickAt(send, saveBtn.x, saveBtn.y);
      console.log(`Clicked: ${saveBtn.text}`);
      await sleep(3000);
    }
  } else {
    console.log("\nNo city input found - may need different approach");
    // Check if we need to navigate back to the location step
    r = await eval_(`return location.href`);
    console.log("Current URL:", r);
  }

  // Final check
  r = await eval_(`
    const text = document.body.innerText;
    const hasSandpoint = text.includes('Sandpoint');
    const hasBuffalo = text.includes('Buffalo');
    return JSON.stringify({ hasSandpoint, hasBuffalo, snippet: text.substring(0, 800) });
  `);
  console.log("\nFinal check:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
