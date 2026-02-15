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

  // Go to contact info
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Click Location Edit
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
  await clickAt(send, JSON.parse(r).x, JSON.parse(r).y);
  console.log("Clicked Location Edit");
  await sleep(2000);

  // Clear city and type Sandpoint
  await eval_(`
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (inp) {
      nativeSetter.call(inp, '');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    }
  `);
  await sleep(300);

  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    inp.focus();
    const rect = inp.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
  `);
  const cityPos = JSON.parse(r);
  await clickAt(send, cityPos.x, cityPos.y);
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(200);
  await send("Input.insertText", { text: "Sandpoint" });
  console.log("Typed Sandpoint");
  await sleep(2000);

  // Click "Sandpoint, ID, US" via JS
  r = await eval_(`
    const opt = Array.from(document.querySelectorAll('li[role="option"]'))
      .find(el => el.offsetParent !== null && el.textContent.includes('Sandpoint, ID'));
    if (opt) { opt.click(); return opt.textContent.trim(); }
    return 'not found';
  `);
  console.log("Selected:", r);
  await sleep(1000);

  // Click Update
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
    if (btn) { btn.click(); return 'clicked'; }
    return 'not found';
  `);
  console.log("Update:", r);
  await sleep(3000);

  // Check for security question
  r = await eval_(`return document.body.innerText.includes('Security question')`);
  console.log("Security question:", r);

  if (r) {
    console.log("\n=== SECURITY QUESTION ===");
    console.log("Question: The name of the street you grew up on");
    console.log("Answer: 120th Street");
    
    // Use React setter to set the answer (more reliable than keyboard)
    await eval_(`
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      const inp = document.querySelector('input[name="securityQuestion[answer]"]');
      if (inp) {
        nativeSetter.call(inp, '120th Street');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        inp.dispatchEvent(new Event('blur', { bubbles: true }));
      }
    `);
    await sleep(300);

    // Verify answer was set
    r = await eval_(`
      const inp = document.querySelector('input[name="securityQuestion[answer]"]');
      return inp ? inp.value : 'not found';
    `);
    console.log("Answer value:", r);

    // Check BOTH checkboxes using JS .click() on the label/container
    r = await eval_(`
      const results = [];
      // lockingNotice checkbox
      const lockCb = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
      if (lockCb && !lockCb.checked) {
        // Try clicking the label or parent
        const label = lockCb.closest('label') || lockCb.parentElement.querySelector('label') || lockCb.parentElement;
        label.click();
        results.push('lockingNotice: clicked label, now ' + lockCb.checked);
        if (!lockCb.checked) {
          // Direct set
          lockCb.checked = true;
          lockCb.dispatchEvent(new Event('change', { bubbles: true }));
          lockCb.dispatchEvent(new Event('click', { bubbles: true }));
          results.push('lockingNotice: set directly, now ' + lockCb.checked);
        }
      } else {
        results.push('lockingNotice: already ' + (lockCb ? lockCb.checked : 'not found'));
      }
      
      // remember checkbox
      const remCb = document.querySelector('input[name="securityQuestion[remember]"]');
      if (remCb && !remCb.checked) {
        const label = remCb.closest('label') || remCb.parentElement.querySelector('label') || remCb.parentElement;
        label.click();
        results.push('remember: clicked label, now ' + remCb.checked);
        if (!remCb.checked) {
          remCb.checked = true;
          remCb.dispatchEvent(new Event('change', { bubbles: true }));
          remCb.dispatchEvent(new Event('click', { bubbles: true }));
          results.push('remember: set directly, now ' + remCb.checked);
        }
      } else {
        results.push('remember: already ' + (remCb ? remCb.checked : 'not found'));
      }
      
      return JSON.stringify(results);
    `);
    console.log("Checkboxes:", r);

    // Verify both checkboxes
    r = await eval_(`
      const lock = document.querySelector('input[name="securityQuestion[lockingNotice]"]');
      const rem = document.querySelector('input[name="securityQuestion[remember]"]');
      return JSON.stringify({
        lockChecked: lock ? lock.checked : 'not found',
        remChecked: rem ? rem.checked : 'not found'
      });
    `);
    console.log("Checkbox state:", r);

    // Click Save using JS
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(el => el.textContent.trim() === 'Save' && el.offsetParent !== null);
      if (btn) { btn.click(); return 'clicked Save'; }
      return 'Save not found';
    `);
    console.log(r);
    await sleep(5000);

    // Check what happened after save
    r = await eval_(`return JSON.stringify({
      url: location.href,
      hasSecQ: document.body.innerText.includes('Security question'),
      hasError: document.body.innerText.includes('Please check'),
      snippet: document.body.innerText.substring(0, 300)
    })`);
    console.log("\nAfter security Q save:", r);
    const afterSave = JSON.parse(r);

    if (!afterSave.hasSecQ) {
      console.log("Security question saved successfully!");
      
      // Now we need to do the city update AGAIN since the first one was lost
      console.log("\n=== RE-DOING CITY UPDATE ===");
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
      
      await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
      await sleep(4000);
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));

      // Edit location again
      await eval_(`window.scrollTo(0, 500)`);
      await sleep(300);
      r = await eval_(`
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
      await clickAt(send, JSON.parse(r).x, JSON.parse(r).y);
      console.log("Clicked Location Edit again");
      await sleep(2000);

      // Clear and type city
      await eval_(`
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        const inp = Array.from(document.querySelectorAll('input'))
          .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
        if (inp) {
          nativeSetter.call(inp, '');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
        }
      `);
      await sleep(300);
      r = await eval_(`
        const inp = Array.from(document.querySelectorAll('input'))
          .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
        inp.focus();
        const rect = inp.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      `);
      const p2 = JSON.parse(r);
      await clickAt(send, p2.x, p2.y);
      await sleep(100);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
      await sleep(200);
      await send("Input.insertText", { text: "Sandpoint" });
      console.log("Typed Sandpoint");
      await sleep(2000);

      // Select from dropdown
      r = await eval_(`
        const opt = Array.from(document.querySelectorAll('li[role="option"]'))
          .find(el => el.offsetParent !== null && el.textContent.includes('Sandpoint, ID'));
        if (opt) { opt.click(); return opt.textContent.trim(); }
        return 'not found';
      `);
      console.log("Selected:", r);
      await sleep(1000);

      // Click Update
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
        if (btn) { btn.click(); return 'clicked'; }
        return 'not found';
      `);
      console.log("Update:", r);
      await sleep(5000);

      // Check result - should NOT trigger security question this time
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
      r = await eval_(`return JSON.stringify({
        url: location.href,
        hasSecQ: document.body.innerText.includes('Security question'),
        hasBuffalo: document.body.innerText.includes('Buffalo'),
        hasSandpoint: document.body.innerText.includes('Sandpoint')
      })`);
      console.log("\nResult:", r);
    } else {
      console.log("Security question still showing - checking for errors...");
      r = await eval_(`
        const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100));
        return JSON.stringify(errors);
      `);
      console.log("Errors:", r);
    }
  }

  // Final verification
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  
  if (!eval_(`return location.href`).includes('contactInfo')) {
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  r = await eval_(`
    const text = document.body.innerText;
    const locIdx = text.indexOf('Location');
    return locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'not found';
  `);
  console.log("\n========== FINAL LOCATION ==========");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
