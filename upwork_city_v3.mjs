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

  // Navigate to contact info
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Scroll and click Location Edit
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(300);

  let r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      return 'ok';
    }
    return 'none';
  `);
  await sleep(300);

  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    const rect = btn.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
  `);
  const editBtn = JSON.parse(r);
  await clickAt(send, editBtn.x, editBtn.y);
  console.log("Clicked Edit");
  await sleep(2000);

  // Get city input position
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (!inp) return JSON.stringify({ error: 'none' });
    inp.scrollIntoView({ block: 'center' });
    return 'scrolled';
  `);
  await sleep(300);

  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    const rect = inp.getBoundingClientRect();
    return JSON.stringify({ val: inp.value, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
  `);
  const city = JSON.parse(r);
  console.log("City:", city.val);

  // Step 1: Clear with React setter
  await eval_(`
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    nativeSetter.call(inp, '');
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
  `);
  await sleep(300);

  // Step 2: Click, Ctrl+A, Backspace
  await clickAt(send, city.x, city.y);
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(200);

  // Step 3: Type "Sandpoint"
  await send("Input.insertText", { text: "Sandpoint" });
  console.log("Typed Sandpoint");
  await sleep(2000);

  // Step 4: Find and click SPECIFICALLY the LI[role="option"] for "Sandpoint, ID, US"
  r = await eval_(`
    const options = Array.from(document.querySelectorAll('li[role="option"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(options);
  `);
  console.log("Options:", r);
  const options = JSON.parse(r);

  const sandpointOption = options.find(o => o.text.includes('Sandpoint, ID'));
  if (sandpointOption) {
    console.log("Clicking: " + sandpointOption.text + " at", sandpointOption.x, sandpointOption.y);
    await clickAt(send, sandpointOption.x, sandpointOption.y);
    await sleep(1500);

    // Verify city was set by the typeahead component
    r = await eval_(`
      const inp = Array.from(document.querySelectorAll('input'))
        .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
      return inp ? inp.value : 'gone';
    `);
    console.log("City after selection:", r);
  } else {
    // Use JS click as fallback
    console.log("No LI option found, trying JS click...");
    r = await eval_(`
      const option = Array.from(document.querySelectorAll('[role="option"]'))
        .find(el => el.textContent.includes('Sandpoint, ID') && el.offsetParent !== null);
      if (option) {
        option.click();
        return 'clicked via JS';
      }
      return 'not found';
    `);
    console.log(r);
    await sleep(1000);
  }

  // Step 5: Verify all fields look good
  r = await eval_(`
    const fields = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null && el.type !== 'hidden' && el.placeholder !== 'Search')
      .map(el => el.placeholder + ': ' + el.value);
    return JSON.stringify(fields, null, 2);
  `);
  console.log("\nAll fields before save:", r);

  // Step 6: Click Update
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  const updBtn = JSON.parse(r);
  if (!updBtn.error) {
    await clickAt(send, updBtn.x, updBtn.y);
    console.log("\nClicked Update");
    await sleep(5000);

    // Handle security question
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    
    r = await eval_(`return document.body.innerText.includes('Security question')`);
    if (r) {
      console.log("Security question appeared!");
      r = await eval_(`
        const inp = document.querySelector('input[name="securityQuestion[answer]"]');
        if (inp) {
          inp.focus();
          const rect = inp.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      const ansPos = JSON.parse(r);
      if (!ansPos.error) {
        await clickAt(send, ansPos.x, ansPos.y);
        await sleep(100);
        await send("Input.insertText", { text: "120th Street" });
        await sleep(200);

        // Check checkbox
        r = await eval_(`
          const cb = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
          if (cb && !cb.checked) {
            cb.click();
            return 'checked';
          }
          return 'already checked or not found';
        `);
        console.log("Checkbox:", r);
        await sleep(200);

        // Save
        r = await eval_(`
          const btn = Array.from(document.querySelectorAll('button'))
            .find(el => el.textContent.trim() === 'Save' && el.offsetParent !== null);
          if (btn) {
            const rect = btn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'none' });
        `);
        const saveBtn = JSON.parse(r);
        if (!saveBtn.error) {
          await clickAt(send, saveBtn.x, saveBtn.y);
          console.log("Saved security question");
          await sleep(5000);
        }
      }
    }

    // Final check
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      const text = document.body.innerText;
      const locIdx = text.indexOf('Location');
      return locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'Location section not found';
    `);
    console.log("\n========== FINAL LOCATION ==========");
    console.log(r);
    
    const hasSandpoint = r.includes('Sandpoint');
    const hasBuffalo = r.includes('Buffalo');
    console.log("\nSandpoint:", hasSandpoint, "| Buffalo:", hasBuffalo);
    if (hasSandpoint && !hasBuffalo) {
      console.log("*** SUCCESS! ***");
    } else if (hasBuffalo) {
      console.log("Still showing Buffalo :(");
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
