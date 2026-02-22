// Fix city from Buffalo to Sandpoint in Contact Info settings
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

async function clearAndTypeField(send, eval_, selector, value) {
  const r = await eval_(`
    const inp = ${selector};
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

  console.log(`  Current: "${pos.val}"`);
  if (pos.val === value) {
    console.log(`  → already correct`);
    return true;
  }

  await sleep(200);
  await clickAt(send, pos.x, pos.y);
  await sleep(200);

  // Triple-click to select all
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 3 });
  await sleep(100);

  // Also Ctrl+A
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
    const inp = ${selector};
    return inp ? inp.value : 'not found';
  `);
  console.log(`  → now: "${v}"`);
  return v === value;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Click the Location Edit button
  console.log("Clicking Location Edit button...");
  await clickAt(send, 1108, 1090);
  await sleep(2000);

  // Check what's visible now
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type,
        placeholder: el.placeholder || '',
        value: el.value,
        name: el.name || '',
        id: el.id || '',
        label: el.labels?.[0]?.textContent?.trim() || ''
      }));
    return JSON.stringify(inputs, null, 2);
  `);
  console.log("Inputs after Edit click:", r);
  const inputs = JSON.parse(r);

  if (inputs.length <= 1) {
    // Maybe need to scroll down and try again
    console.log("Not many inputs found, scrolling and retrying...");
    await eval_(`window.scrollTo(0, 800)`);
    await sleep(500);
    
    // Re-find the location Edit button
    r = await eval_(`
      const editBtns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      // Also check nearby text
      const locationText = Array.from(document.querySelectorAll('*'))
        .find(el => el.textContent.includes('Buffalo') && el.offsetParent !== null && el.children.length < 3);
      const locRect = locationText ? locationText.getBoundingClientRect() : null;
      return JSON.stringify({ editBtns, locRect: locRect ? { x: Math.round(locRect.x), y: Math.round(locRect.y) } : null });
    `);
    console.log("Edit buttons after scroll:", r);
    const { editBtns } = JSON.parse(r);
    
    // Click the second Edit button (for Location section)
    if (editBtns.length >= 2) {
      await clickAt(send, editBtns[1].x, editBtns[1].y);
      console.log("Clicked second Edit button at", editBtns[1].x, editBtns[1].y);
      await sleep(2000);
      
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            tag: el.tagName, type: el.type,
            placeholder: el.placeholder || '',
            value: el.value,
            name: el.name || '',
            id: el.id || ''
          }));
        return JSON.stringify(inputs, null, 2);
      `);
      console.log("Inputs now:", r);
    }
  }

  // Look for city-related input
  r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input, select'))
      .filter(el => el.offsetParent !== null);
    const cityInput = allInputs.find(el => 
      el.name?.toLowerCase().includes('city') || 
      el.id?.toLowerCase().includes('city') ||
      el.placeholder?.toLowerCase().includes('city') ||
      el.value === 'Buffalo'
    );
    if (cityInput) {
      cityInput.scrollIntoView({ block: 'center' });
      const rect = cityInput.getBoundingClientRect();
      return JSON.stringify({
        found: true,
        tag: cityInput.tagName, type: cityInput.type,
        name: cityInput.name, id: cityInput.id,
        placeholder: cityInput.placeholder,
        value: cityInput.value,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    
    // Check all text content for Buffalo or form with address
    const formElements = allInputs.map(el => ({
      tag: el.tagName, type: el.type, name: el.name, id: el.id,
      placeholder: el.placeholder || '', value: el.value
    }));
    return JSON.stringify({ found: false, formElements });
  `);
  console.log("\nCity input search:", r);

  const cityResult = JSON.parse(r);
  if (cityResult.found) {
    console.log("\nFound city input! Fixing...");
    
    // Click the city input
    await clickAt(send, cityResult.x, cityResult.y);
    await sleep(200);
    
    // Select all and delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(100);
    
    // Type Sandpoint
    await send("Input.insertText", { text: "Sandpoint" });
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
    r = await eval_(`
      const inp = document.querySelector('input[value="Sandpoint"], input[name*="city"], input[id*="city"]');
      return inp ? inp.value : 'not found directly';
    `);
    console.log("City after fix:", r);

    // Also fix timezone if possible - should be Pacific, not Central
    r = await eval_(`
      const tzSelect = Array.from(document.querySelectorAll('select'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          name: el.name, id: el.id, value: el.value,
          options: Array.from(el.options).slice(0, 5).map(o => o.text.substring(0, 40) + ':' + o.value)
        }));
      return JSON.stringify(tzSelect, null, 2);
    `);
    console.log("\nTimezone selects:", r);

    // Find and click Save/Update button
    await sleep(500);
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(btns);
    `);
    console.log("Buttons:", r);
    const btns = JSON.parse(r);
    const saveBtn = btns.find(b => b.text.includes('Save') || b.text.includes('Update') || b.text.includes('Submit'));
    if (saveBtn) {
      await clickAt(send, saveBtn.x, saveBtn.y);
      console.log(`Clicked: ${saveBtn.text}`);
      await sleep(3000);
      
      // Verify the change
      r = await eval_(`
        return document.body.innerText.includes('Sandpoint') ? 'SUCCESS: Sandpoint found!' : 
               document.body.innerText.includes('Buffalo') ? 'STILL Buffalo' : 'Unknown';
      `);
      console.log("\nResult:", r);
    }
  } else {
    console.log("\nNo city input found. Available form elements:", JSON.stringify(cityResult.formElements, null, 2));
  }

  // Final page check
  r = await eval_(`
    const text = document.body.innerText;
    const hasSandpoint = text.includes('Sandpoint');
    const hasBuffalo = text.includes('Buffalo');
    return JSON.stringify({ hasSandpoint, hasBuffalo });
  `);
  console.log("\nFinal:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
