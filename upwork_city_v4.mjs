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

async function editCityToSandpoint(ws, send, eval_) {
  // Scroll and click Location Edit
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(300);

  let r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    btn.scrollIntoView({ block: 'center' });
    return 'ok';
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
  console.log("Clicked Location Edit");
  await sleep(2000);

  // Clear city field
  await eval_(`
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (inp) {
      inp.scrollIntoView({ block: 'center' });
      nativeSetter.call(inp, '');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    }
  `);
  await sleep(300);

  // Click and clear with keyboard
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    inp.focus();
    const rect = inp.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
  `);
  const pos = JSON.parse(r);
  await clickAt(send, pos.x, pos.y);
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(200);

  // Type Sandpoint
  await send("Input.insertText", { text: "Sandpoint" });
  console.log("Typed Sandpoint");
  await sleep(2000);

  // Click the LI option
  r = await eval_(`
    const options = Array.from(document.querySelectorAll('li[role="option"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('Sandpoint, ID'))
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(options);
  `);
  const opts = JSON.parse(r);
  console.log("Options:", r);

  if (opts.length > 0) {
    // Use JS click directly on the LI element for more reliability
    r = await eval_(`
      const opt = Array.from(document.querySelectorAll('li[role="option"]'))
        .find(el => el.offsetParent !== null && el.textContent.includes('Sandpoint, ID'));
      if (opt) {
        opt.click();
        return 'clicked via JS';
      }
      return 'not found';
    `);
    console.log("JS click:", r);
    await sleep(1000);
  }

  // Verify
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return inp ? inp.value : 'gone';
  `);
  console.log("City after JS click:", r);

  // Click Update
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
    console.log("Clicked Update");
    return true;
  }
  return false;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // PHASE 1: Set up security question first (if not already done)
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Make a dummy edit attempt to trigger security question
  console.log("=== PHASE 1: Setting up security question ===");
  await editCityToSandpoint(ws, send, eval_);
  await sleep(5000);

  // Check for security question
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  let r = await eval_(`return document.body.innerText.includes('Security question')`);
  console.log("\nSecurity question appeared:", r);

  if (r) {
    console.log("Answering security question...");
    
    // Focus answer field and type
    r = await eval_(`
      const inp = document.querySelector('input[name="securityQuestion[answer]"]');
      if (inp) {
        inp.focus();
        inp.click();
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

      // Click checkbox using CDP click (not JS)
      r = await eval_(`
        const cb = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
        if (cb && !cb.checked) {
          const label = cb.closest('label') || cb.parentElement;
          const rect = (label || cb).getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ checked: cb ? cb.checked : 'not found' });
      `);
      console.log("Checkbox info:", r);
      const cbInfo = JSON.parse(r);
      if (cbInfo.x) {
        await clickAt(send, cbInfo.x, cbInfo.y);
        console.log("Clicked checkbox");
        await sleep(300);
      }

      // Click Save
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
        console.log("Clicked Save");
        await sleep(5000);
      }
    }

    // Verify security question was saved
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    r = await eval_(`return document.body.innerText.includes('Security question')`);
    console.log("Still showing security question:", r);
    
    if (r) {
      console.log("Security question dialog still there. Checking status...");
      r = await eval_(`return document.body.innerText.substring(0, 500)`);
      console.log(r);
    }
  }

  // PHASE 2: Now do the actual city update
  console.log("\n=== PHASE 2: Updating city to Sandpoint ===");
  
  // Navigate back to contact info
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Do the city edit again
  const updated = await editCityToSandpoint(ws, send, eval_);
  
  if (updated) {
    await sleep(5000);
    
    // Check if security question appears again
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    
    r = await eval_(`return document.body.innerText.includes('Security question')`);
    if (r) {
      console.log("\nSecurity question AGAIN - it's not saving properly");
      // Try to answer again but use both checkboxes
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
        await sleep(300);

        // Check BOTH checkboxes
        r = await eval_(`
          const cbs = document.querySelectorAll('input[type="checkbox"]');
          const results = [];
          cbs.forEach(cb => {
            if (cb.offsetParent !== null && !cb.checked) {
              const rect = cb.getBoundingClientRect();
              results.push({ name: cb.name, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          });
          return JSON.stringify(results);
        `);
        console.log("Unchecked checkboxes:", r);
        const checkboxes = JSON.parse(r);
        for (const cb of checkboxes) {
          await clickAt(send, cb.x, cb.y);
          console.log("Checked:", cb.name);
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
          return JSON.stringify({ error: 'none' });
        `);
        const saveBtn2 = JSON.parse(r);
        if (!saveBtn2.error) {
          await clickAt(send, saveBtn2.x, saveBtn2.y);
          console.log("Saved");
          await sleep(5000);
        }
      }
    }

    // FINAL CHECK
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      const text = document.body.innerText;
      const locIdx = text.indexOf('Location');
      return locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'not found';
    `);
    console.log("\n========== FINAL ==========");
    console.log(r);
    console.log("Sandpoint:", r.includes('Sandpoint'));
    console.log("Buffalo:", r.includes('Buffalo'));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
