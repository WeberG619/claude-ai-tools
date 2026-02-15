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
  let r = await eval_(`return location.href`);
  if (!r.includes('contactInfo')) {
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // Scroll to Location section
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(300);

  // Click Location Edit button
  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      return 'scrolled';
    }
    return 'none';
  `);
  await sleep(300);

  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null);
    const btn = editBtns[editBtns.length - 1];
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  const editBtn = JSON.parse(r);
  console.log("Edit btn:", r);
  await clickAt(send, editBtn.x, editBtn.y);
  await sleep(2000);

  // Find city input
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (inp) {
      const rect = inp.getBoundingClientRect();
      return JSON.stringify({ val: inp.value, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("City:", r);
  const cityInfo = JSON.parse(r);

  if (cityInfo.error) {
    console.log("No city input found!");
    ws.close();
    return;
  }

  // Use React setter to clear, then type via keyboard
  console.log(`Current city: "${cityInfo.val}"`);

  // Step 1: Clear with React setter
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

  // Verify cleared
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return inp ? inp.value : 'gone';
  `);
  console.log("After clear:", r);

  // Step 2: Click the city input field
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    if (inp) {
      inp.focus();
      const rect = inp.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'gone' });
  `);
  const pos = JSON.parse(r);
  await clickAt(send, pos.x, pos.y);
  await sleep(200);

  // Step 3: Also try Ctrl+A + Backspace in case React setter didn't fully clear
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(200);

  // Verify cleared again
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return inp ? inp.value : 'gone';
  `);
  console.log("After Ctrl+A+BS:", r);

  // Step 4: Type "Sandpoint" using insertText
  await send("Input.insertText", { text: "Sandpoint" });
  console.log("Typed Sandpoint");
  await sleep(2000);

  // Check value and suggestions
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    const value = inp ? inp.value : 'gone';
    
    // Look for dropdown/suggestions
    const allVisible = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        if (!el.offsetParent) return false;
        const rect = el.getBoundingClientRect();
        const text = el.textContent.trim();
        return text.includes('Sandpoint') && el.children.length < 3 && rect.width > 50 && el.tagName !== 'INPUT';
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 80),
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    
    return JSON.stringify({ value, suggestions: allVisible });
  `);
  console.log("Value + suggestions:", r);
  const result = JSON.parse(r);

  // Find and click Sandpoint suggestion
  const sugg = result.suggestions.find(s => 
    s.text.includes('Sandpoint') && !s.text.includes('value')
  );
  if (sugg) {
    await clickAt(send, sugg.x, sugg.y);
    console.log("Clicked suggestion:", sugg.text);
    await sleep(1000);
  } else {
    console.log("No clickable suggestion found. Tabbing out...");
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(500);
  }

  // Verify final city value
  r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === 'Start typing your city' && el.offsetParent !== null);
    return inp ? inp.value : 'gone';
  `);
  console.log("\nFinal city value:", r);

  // Check all fields
  r = await eval_(`
    const fields = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null && el.type !== 'hidden' && el.placeholder !== 'Search')
      .map(el => el.placeholder + ': ' + el.value);
    return JSON.stringify(fields);
  `);
  console.log("All fields:", r);

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
    console.log("\nClicked Update");
    await sleep(5000);

    // Handle security question
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    
    r = await eval_(`return document.body.innerText.includes('Security question') || document.body.innerText.includes('security question')`);
    if (r) {
      console.log("Security question! Answering...");
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
            const rect = cb.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x), y: Math.round(rect.y) });
          }
          return JSON.stringify({ ok: true });
        `);
        const cbPos = JSON.parse(r);
        if (cbPos.x) {
          await clickAt(send, cbPos.x, cbPos.y);
          await sleep(200);
        }

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

    // Reload and verify
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      const text = document.body.innerText;
      const locIdx = text.indexOf('Location');
      return locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'Location not found';
    `);
    console.log("\n=== LOCATION SECTION ===");
    console.log(r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
