// Final fix: triple-click city field, replace with Sandpoint, select from dropdown
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

async function tripleClickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  // Click 1
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  // Click 2
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 2 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 2 });
  await sleep(50);
  // Click 3
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 3 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 3 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Navigate to contact info
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Verify we're there
  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  // Scroll and find Location Edit
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(500);

  // Click Location Edit (last Edit button)
  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      await new Promise(r => setTimeout(r, 200));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no edit' });
  `);
  console.log("Edit button:", r);
  const editBtn = JSON.parse(r);
  await clickAt(send, editBtn.x, editBtn.y);
  await sleep(2000);

  // Find city input
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (cityInput) {
      cityInput.scrollIntoView({ block: 'center' });
      const rect = cityInput.getBoundingClientRect();
      return JSON.stringify({ 
        value: cityInput.value,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        left: Math.round(rect.x + 5),
        right: Math.round(rect.x + rect.width - 30)
      });
    }
    return JSON.stringify({ error: 'no city input' });
  `);
  console.log("City field:", r);
  const city = JSON.parse(r);

  if (city.error) {
    console.log("ERROR: Can't find city input");
    ws.close();
    return;
  }

  console.log(`City value: "${city.value}"`);

  // Strategy: Use JS to clear the field value directly, then use keyboard to type
  // This bypasses the typeahead's resistance to clearing
  await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (cityInput) {
      // Use React's native setter to clear
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(cityInput, '');
      cityInput.dispatchEvent(new Event('input', { bubbles: true }));
      cityInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  `);
  await sleep(500);

  // Verify it's cleared
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return cityInput ? cityInput.value : 'not found';
  `);
  console.log("After JS clear:", r);

  // Now focus the input and type Sandpoint using keyboard
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (cityInput) {
      cityInput.focus();
      cityInput.click();
      const rect = cityInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'gone' });
  `);
  const focusPos = JSON.parse(r);
  await clickAt(send, focusPos.x, focusPos.y);
  await sleep(200);

  // Type S-a-n-d-p-o-i-n-t one character at a time with dispatchKeyEvent
  const chars = "Sandpoint";
  for (const char of chars) {
    await send("Input.dispatchKeyEvent", { 
      type: "keyDown", 
      key: char,
      text: char
    });
    await send("Input.dispatchKeyEvent", { 
      type: "keyUp", 
      key: char 
    });
    await sleep(100);
  }
  console.log("Typed 'Sandpoint' char by char");
  await sleep(2000);

  // Check current value
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return cityInput ? cityInput.value : 'not found';
  `);
  console.log("City value now:", r);

  // Check for dropdown suggestions
  r = await eval_(`
    const items = Array.from(document.querySelectorAll('li, [role="option"], [role="listbox"] *'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return rect.y > 600 && rect.y < 800; // Near the city input area
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(items, null, 2);
  `);
  console.log("Suggestions near city:", r);
  let suggestions = JSON.parse(r);

  // If no suggestions found, look more broadly
  if (suggestions.length === 0) {
    r = await eval_(`
      const all = Array.from(document.querySelectorAll('*'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('Sandpoint') && el.children.length === 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(all);
    `);
    console.log("Sandpoint anywhere:", r);
    suggestions = JSON.parse(r);
  }

  // Click the Sandpoint suggestion
  const sandpoint = suggestions.find(s => s.text.includes('Sandpoint') && s.tag !== 'INPUT');
  if (sandpoint) {
    await clickAt(send, sandpoint.x, sandpoint.y);
    console.log("Selected:", sandpoint.text);
    await sleep(1000);
  }

  // Verify city value
  r = await eval_(`
    const cityInput = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return cityInput ? cityInput.value : 'not found';
  `);
  console.log("\nCity final value:", r);

  // Verify ALL form fields
  r = await eval_(`
    const fields = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null && el.type !== 'hidden')
      .map(el => ({ placeholder: el.placeholder || el.type, value: el.value }));
    return JSON.stringify(fields, null, 2);
  `);
  console.log("All fields:", r);

  // Click Update
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no update' });
  `);
  const updateBtn = JSON.parse(r);
  if (!updateBtn.error) {
    await clickAt(send, updateBtn.x, updateBtn.y);
    console.log("\nClicked Update");
    await sleep(5000);

    // Handle security question if it appears
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href,
      hasSecQ: document.body.innerText.includes('security question') || document.body.innerText.includes('Security question'),
      bodySnippet: document.body.innerText.substring(0, 300)
    })`);
    console.log("After update:", r);
    const afterUpdate = JSON.parse(r);

    if (afterUpdate.hasSecQ) {
      console.log("\nSecurity question appeared. Answering...");
      
      // Type answer
      r = await eval_(`
        const inp = document.querySelector('input[name="securityQuestion[answer]"]');
        if (inp) {
          inp.focus();
          const rect = inp.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no input' });
      `);
      const ansPos = JSON.parse(r);
      if (!ansPos.error) {
        await clickAt(send, ansPos.x, ansPos.y);
        await sleep(200);
        await send("Input.insertText", { text: "120th Street" });
        await sleep(300);

        // Check checkbox
        r = await eval_(`
          const cb = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
          if (cb && !cb.checked) {
            const rect = cb.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ ok: true });
        `);
        const cbPos = JSON.parse(r);
        if (cbPos.x) {
          await clickAt(send, cbPos.x, cbPos.y);
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
          console.log("Saved security question");
          await sleep(5000);
        }
      }

      // Reload and check
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
      await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
      await sleep(4000);
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    }

    // Final verification
    r = await eval_(`
      const text = document.body.innerText;
      const locIdx = text.indexOf('Location');
      return JSON.stringify({
        hasSandpoint: text.includes('Sandpoint'),
        hasBuffalo: text.includes('Buffalo'),
        location: locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'not found'
      });
    `);
    console.log("\n=== FINAL ===");
    console.log(r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
