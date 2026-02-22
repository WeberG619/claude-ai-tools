// Simple: Navigate to contact info, edit location, fix city to Sandpoint
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Make sure we're on contact info page
  let r = await eval_(`return location.href`);
  if (!r.includes('contactInfo')) {
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // Scroll down and click Location Edit
  await eval_(`window.scrollTo(0, 600)`);
  await sleep(500);

  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    // Last edit button is for Location
    const btn = editBtns[editBtns.length - 1];
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no edit btn' });
  `);
  const editBtn = JSON.parse(r);
  console.log("Location Edit button:", r);
  
  await clickAt(send, editBtn.x, editBtn.y);
  console.log("Clicked Location Edit");
  await sleep(2000);

  // Find the city input by placeholder
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input[type="search"]'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (cityInput) {
      cityInput.scrollIntoView({ block: 'center' });
      const rect = cityInput.getBoundingClientRect();
      return JSON.stringify({ 
        value: cityInput.value, 
        x: Math.round(rect.x + rect.width/2), 
        y: Math.round(rect.y + rect.height/2) 
      });
    }
    return JSON.stringify({ error: 'no city input' });
  `);
  console.log("City input:", r);
  const cityInfo = JSON.parse(r);

  if (cityInfo.error) {
    console.log("City input not found!");
    ws.close();
    return;
  }

  console.log(`City value: "${cityInfo.value}"`);

  // Find the Clear button for city (it's near the city input)
  // First, look for Clear Input buttons
  r = await eval_(`
    const clearBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.includes('Clear Input') && el.offsetParent !== null)
      .map(el => ({
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(clearBtns);
  `);
  console.log("Clear buttons:", r);
  const clearBtns = JSON.parse(r);

  // The second Clear button should be for city (first is for address)
  if (clearBtns.length >= 2) {
    await clickAt(send, clearBtns[1].x, clearBtns[1].y);
    console.log("Clicked city Clear button");
    await sleep(500);
  } else {
    // Manual clear: click, select all, delete
    await clickAt(send, cityInfo.x, cityInfo.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(100);
  }

  // Focus the city input and type Sandpoint
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input[type="search"]'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (cityInput) {
      cityInput.focus();
      cityInput.click();
      const rect = cityInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: cityInput.value });
    }
    return JSON.stringify({ error: 'lost city input' });
  `);
  console.log("City after clear:", r);
  const cityAfter = JSON.parse(r);
  
  if (!cityAfter.error) {
    await clickAt(send, cityAfter.x, cityAfter.y);
    await sleep(200);
    await send("Input.insertText", { text: "Sandpoint" });
    console.log("Typed 'Sandpoint'");
    await sleep(1500);

    // Check for typeahead suggestions
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('li, [role="option"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('Sandpoint'))
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    console.log("Suggestions:", r);
    const suggestions = JSON.parse(r);

    if (suggestions.length > 0) {
      // Pick Sandpoint, ID
      const pick = suggestions.find(s => s.text.includes('Idaho') || s.text.includes('ID')) || suggestions[0];
      await clickAt(send, pick.x, pick.y);
      console.log("Selected:", pick.text);
      await sleep(1000);
    } else {
      console.log("No suggestions found - escaping and tabbing...");
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
      await sleep(300);
    }
  }

  // Verify fields before saving
  r = await eval_(`
    const fields = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null && el.type !== 'hidden')
      .map(el => ({ placeholder: el.placeholder || el.type, value: el.value }));
    return JSON.stringify(fields, null, 2);
  `);
  console.log("\nFields before save:", r);

  // Click Update
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no update btn' });
  `);
  const updateBtn = JSON.parse(r);
  console.log("Update button:", r);

  if (!updateBtn.error) {
    await clickAt(send, updateBtn.x, updateBtn.y);
    console.log("Clicked Update!");
    await sleep(5000);

    // Check for security question or success
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href,
      hasSecQ: document.body.innerText.includes('security question'),
      hasSandpoint: document.body.innerText.includes('Sandpoint'),
      hasBuffalo: document.body.innerText.includes('Buffalo'),
      snippet: document.body.innerText.substring(0, 400)
    })`);
    console.log("\n=== AFTER UPDATE ===");
    console.log(r);
    const result = JSON.parse(r);

    if (result.hasSecQ) {
      console.log("\nSecurity question popped up again. Answering with '120th Street'...");
      
      // Answer the security question
      r = await eval_(`
        const ansInput = document.querySelector('input[name="securityQuestion[answer]"]');
        if (ansInput) {
          ansInput.scrollIntoView({ block: 'center' });
          ansInput.focus();
          const rect = ansInput.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: ansInput.value });
        }
        return JSON.stringify({ error: 'no answer input' });
      `);
      const ansInfo = JSON.parse(r);
      
      if (!ansInfo.error) {
        await clickAt(send, ansInfo.x, ansInfo.y);
        await sleep(200);
        // Clear any existing text
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await sleep(100);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(100);
        await send("Input.insertText", { text: "120th Street" });
        await sleep(300);

        // Check the locking notice checkbox
        r = await eval_(`
          const cb = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
          if (cb && !cb.checked) {
            const rect = cb.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ checked: true });
        `);
        const cbInfo = JSON.parse(r);
        if (cbInfo.x) {
          await clickAt(send, cbInfo.x, cbInfo.y);
          await sleep(200);
        }

        // Click Save
        r = await eval_(`
          const btn = Array.from(document.querySelectorAll('button'))
            .find(el => el.textContent.trim() === 'Save' && el.offsetParent !== null);
          if (btn) {
            const rect = btn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'no save' });
        `);
        const saveBtn = JSON.parse(r);
        if (!saveBtn.error) {
          await clickAt(send, saveBtn.x, saveBtn.y);
          console.log("Clicked Save on security question");
          await sleep(5000);

          // Check final state
          ws.close();
          await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          
          await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
          await sleep(4000);
          ws.close();
          await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));

          r = await eval_(`
            const text = document.body.innerText;
            const locIdx = text.indexOf('Location');
            return JSON.stringify({
              hasSandpoint: text.includes('Sandpoint'),
              hasBuffalo: text.includes('Buffalo'),
              locationSection: locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'not found'
            });
          `);
          console.log("\n=== FINAL RESULT ===");
          console.log(r);
        }
      }
    } else if (result.hasSandpoint && !result.hasBuffalo) {
      console.log("\n*** SUCCESS! City changed to Sandpoint! ***");
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
