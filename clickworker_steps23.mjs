const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(30);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  console.log("=== STEP 2: Personal Details ===");

  // Fix overflow first
  await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) contentDiv.style.overflow = 'auto';
  `);

  // Birthday
  let r = await eval_(`
    const el = document.querySelector('#user_date_of_birth');
    if (el) {
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      set.call(el, '1975-06-15');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set';
    }
    return 'not found';
  `);
  console.log("Birthday:", r);

  // Country
  r = await eval_(`
    const sel = document.querySelector('#user_address_country');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === 'United States') {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'not found';
  `);
  console.log("Country:", r);
  await sleep(500); // Wait for state dropdown to populate

  // Language
  r = await eval_(`
    const sel = document.querySelector('#user_native_languages');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text.includes('English USA')) {
        sel.options[i].selected = true;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'not found';
  `);
  console.log("Language:", r);

  // Street
  r = await eval_(`
    const el = document.querySelector('#user_address_street');
    const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    set.call(el, '786 NW 5th St');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'set';
  `);
  console.log("Street:", r);

  // Zip
  r = await eval_(`
    const el = document.querySelector('#user_address_postal_code');
    const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    set.call(el, '33136');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'set';
  `);
  console.log("Zip:", r);

  // City
  r = await eval_(`
    const el = document.querySelector('#user_address_city');
    const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    set.call(el, 'Miami');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'set';
  `);
  console.log("City:", r);

  // State - Florida
  r = await eval_(`
    const sel = document.querySelector('#user_address_state');
    if (!sel) return 'state field not found (may not have loaded yet)';
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === 'Florida') {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'Florida not found';
  `);
  console.log("State:", r);

  // Phone code
  r = await eval_(`
    const sel = document.querySelector('#user_address_phone_code');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === '+1' || sel.options[i].value === '1') {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'not found';
  `);
  console.log("Phone code:", r);

  // Phone number
  r = await eval_(`
    const el = document.querySelector('#user_address_phone_number');
    const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    set.call(el, '7865879726');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'set';
  `);
  console.log("Phone:", r);

  // Age checkbox
  r = await eval_(`
    const cb = document.querySelector('#user_agreements_is_full_age');
    if (cb && !cb.checked) { cb.click(); return 'checked'; }
    return cb ? 'already checked' : 'not found';
  `);
  console.log("Age:", r);

  // T&C checkbox
  r = await eval_(`
    const cb = document.querySelector('#user_agreements_general_5908');
    if (cb && !cb.checked) { cb.click(); return 'checked'; }
    return cb ? 'already checked' : 'not found';
  `);
  console.log("T&C:", r);
  await sleep(200);

  // Click Continue on Step 2
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    // Get the visible Continue buttons
    const visible = btns.filter(b => b.textContent.trim() === 'Continue' && b.offsetParent !== null);
    if (visible.length > 0) {
      visible[0].scrollIntoView({ block: 'center' });
      await new Promise(r => setTimeout(r, 300));
      const rect = visible[0].getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
    }
    // Try scrolling any Continue into view
    const anyContinue = btns.filter(b => b.textContent.trim() === 'Continue');
    if (anyContinue.length > 1) {
      // Second Continue is for step 2
      anyContinue[1].scrollIntoView({ block: 'center' });
      await new Promise(r => setTimeout(r, 300));
      const rect = anyContinue[1].getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), idx: 1 });
    }
    return 'not found';
  `);
  console.log("\nStep 2 Continue:", r);

  let advanced = false;
  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (pos.w > 0 && pos.y > 0 && pos.y < 1200) {
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Continue for Step 2");
      advanced = true;
    } else {
      // JS click on the second Continue button
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.trim() === 'Continue');
        if (btns.length > 1) { btns[1].click(); return 'js clicked idx 1'; }
        if (btns.length > 0) { btns[0].click(); return 'js clicked idx 0'; }
        return 'not found';
      `);
      console.log("JS click Step 2:", r);
      advanced = r.includes('clicked');
    }
  }

  if (advanced) {
    await sleep(3000);

    // Verify step 3
    r = await eval_(`
      const active = document.querySelector('.nav-link.active');
      const text = active?.textContent?.trim().substring(0, 20);
      const mobileCheckbox = document.querySelector('#mobile_app_installed');
      return JSON.stringify({ activeStep: text, mobileCheckboxVisible: mobileCheckbox?.offsetParent !== null || false });
    `);
    console.log("\n=== Step after advance:", r);

    const stepInfo = JSON.parse(r);

    if (stepInfo.mobileCheckboxVisible || stepInfo.activeStep?.includes('3')) {
      console.log("\n=== STEP 3: Finish ===");

      // Check mobile app checkbox
      r = await eval_(`
        const cb = document.querySelector('#mobile_app_installed');
        if (cb && !cb.checked) { cb.click(); return 'checked'; }
        return cb ? 'already checked' : 'not found';
      `);
      console.log("Mobile checkbox:", r);
      await sleep(200);

      // Find the Finish submit button (it's input[type=submit], not button)
      r = await eval_(`
        const submit = document.querySelector('input[type="submit"]');
        if (submit) {
          submit.scrollIntoView({ block: 'center' });
          await new Promise(r => setTimeout(r, 300));
          const rect = submit.getBoundingClientRect();
          return JSON.stringify({ value: submit.value, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), disabled: submit.disabled });
        }
        return 'not found';
      `);
      console.log("Finish button:", r);

      if (r !== 'not found') {
        const pos = JSON.parse(r);
        if (pos.w > 0 && pos.y > 0 && pos.y < 1200) {
          await clickAt(send, pos.x, pos.y);
          console.log("CDP clicked Finish at", pos.x, pos.y);
        } else {
          // JS click
          r = await eval_(`
            const submit = document.querySelector('input[type="submit"]');
            if (submit) { submit.click(); return 'clicked'; }
            return 'not found';
          `);
          console.log("JS click Finish:", r);
        }

        await sleep(15000);

        r = await eval_(`return window.location.href`);
        console.log("\nURL:", r);
        r = await eval_(`return document.body.innerText.substring(0, 3000)`);
        console.log("\nPage:", r);
      }
    } else {
      console.log("Not on Step 3 yet. Checking errors...");
      r = await eval_(`
        const errors = document.querySelectorAll('[class*="error"], .invalid-feedback, .field_with_errors');
        return JSON.stringify(Array.from(errors).filter(e => e.textContent.trim().length > 0 && e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 80)));
      `);
      console.log("Errors:", r);
    }
  }

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
