// Fix all Upwork fields: rate $50, correct address, DOB, phone
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

async function setInputValue(eval_, placeholder, value) {
  const r = await eval_(`
    const inp = Array.from(document.querySelectorAll('input'))
      .find(el => el.placeholder === '${placeholder}' && el.offsetParent !== null);
    if (inp) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inp, '${value}');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      inp.dispatchEvent(new Event('blur', { bubbles: true }));
      return inp.value;
    }
    return 'NOT FOUND';
  `);
  return r;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  let r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Current step:", r);

  // === FIX RATE: Go back to rate page ===
  if (r === 'location') {
    console.log("Going back to rate...");
    await eval_(`
      const back = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Back');
      if (back) back.click();
    `);
    await sleep(3000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("Step:", r);

  if (r === 'rate') {
    // Use React setter to directly set value to 50
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input.air3-input'))
        .filter(el => el.offsetParent !== null && !el.disabled);
      if (inputs.length > 0) {
        const inp = inputs[0];
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, '50');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        inp.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'set to 50: ' + inp.value;
      }
      return 'no input found';
    `);
    console.log("Rate setter:", r);
    await sleep(1000);

    // Check values
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input.air3-input'))
        .filter(el => el.offsetParent !== null);
      return JSON.stringify(inputs.map(i => ({ val: i.value, disabled: i.disabled })));
    `);
    console.log("Rate values:", r);

    // Click Next
    await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null && !b.textContent.includes('Skip to'));
      if (btn) btn.click();
    `);
    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // === FILL LOCATION PAGE ===
  r = await eval_(`return location.href.split('/').pop().split('?')[0]`);
  console.log("\nNow on:", r);

  if (r === 'location') {
    console.log("=== Setting all fields via React setter ===");

    // Set DOB
    let v = await setInputValue(eval_, "mm/dd/yyyy", "03/18/1974");
    console.log("DOB:", v);

    // Set address - DON'T use autocomplete, just set directly
    v = await setInputValue(eval_, "Enter street address", "619 Hopkins Rd");
    console.log("Street:", v);

    // Set city
    v = await setInputValue(eval_, "Enter city", "Sandpoint");
    console.log("City:", v);

    // Set state
    v = await setInputValue(eval_, "Enter state/province", "ID");
    console.log("State:", v);

    // Set ZIP
    v = await setInputValue(eval_, "Enter ZIP/Postal code", "83864");
    console.log("ZIP:", v);

    // Set phone
    v = await setInputValue(eval_, "Enter number", "2083551234");
    console.log("Phone:", v);

    await sleep(1000);

    // Check for errors
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify(errors);
    `);
    console.log("Errors:", r);

    // Check if photo is required
    r = await eval_(`
      const body = document.body.innerText;
      const hasPhotoError = body.includes('Add a profile photo') || body.includes('photo is required');
      const photoBtn = document.querySelector('[data-test="photo"] button, [class*="photo"] button');
      return JSON.stringify({ hasPhotoError, photoBtn: !!photoBtn });
    `);
    console.log("Photo status:", r);

    // Verify all fields
    r = await eval_(`
      const fields = {};
      Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
        fields[inp.placeholder || inp.type] = inp.value;
      });
      return JSON.stringify(fields);
    `);
    console.log("All fields:", r);

    // Try clicking Review
    console.log("\nClicking Review...");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    await sleep(300);
    const btn = JSON.parse(r);
    if (!btn.error) {
      await clickAt(send, btn.x, btn.y);
      await sleep(3000);

      // Check if page advanced
      r = await eval_(`
        const url = location.href;
        const step = url.split('/').pop().split('?')[0];
        const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
          .map(el => el.textContent.trim().substring(0, 100));
        const body = document.body.innerText.substring(0, 500);
        return JSON.stringify({ url, step, errors, body });
      `);
      const state = JSON.parse(r);
      console.log("After Review:", state.step);
      console.log("Errors:", JSON.stringify(state.errors));
      console.log("Body:", state.body.substring(0, 300));

      if (state.step !== 'location') {
        // We advanced! Check for Submit
        await sleep(2000);
        ws.close(); await sleep(500);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));

        r = await eval_(`
          const btns = Array.from(document.querySelectorAll('button'))
            .filter(el => el.offsetParent !== null && !el.textContent.includes('Skip to'))
            .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
          return JSON.stringify(btns);
        `);
        console.log("\nButtons on new page:", r);
        const btns = JSON.parse(r);
        const submit = btns.find(b => b.text.includes('Submit') || b.text.includes('Publish'));
        if (submit) {
          await clickAt(send, submit.x, submit.y);
          console.log(`Clicked: ${submit.text}`);
          await sleep(8000);
          ws.close(); await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
          console.log("\n*** RESULT:", r);
        }
      } else {
        console.log("Still on location - validation preventing advance");
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
