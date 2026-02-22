// Fix phone number to 786-587-9726, close dialog, re-submit
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

  // Step 1: Close the verification dialog if open
  let r = await eval_(`
    const closeBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Close the dialog' && b.offsetParent !== null);
    if (closeBtn) {
      closeBtn.click();
      return 'dialog closed';
    }
    return 'no dialog';
  `);
  console.log("Dialog:", r);
  await sleep(1000);

  // Step 2: Update main phone field to correct number
  console.log("Setting phone to 7865879726...");
  r = await eval_(`
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    // Find the FIRST phone input (main form, not dialog)
    const phoneInputs = Array.from(document.querySelectorAll('input[type="tel"]'))
      .filter(el => el.offsetParent !== null);
    if (phoneInputs.length > 0) {
      const mainPhone = phoneInputs[0];
      setter.call(mainPhone, '7865879726');
      mainPhone.dispatchEvent(new Event('input', { bubbles: true }));
      mainPhone.dispatchEvent(new Event('change', { bubbles: true }));
      mainPhone.dispatchEvent(new Event('blur', { bubbles: true }));
      return 'phone set: ' + mainPhone.value;
    }
    return 'no phone input';
  `);
  console.log(r);
  await sleep(500);

  // Also ensure all other fields are still set
  r = await eval_(`
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const fields = [
      ['mm/dd/yyyy', '03/18/1974'],
      ['Enter street address', '619 Hopkins Rd'],
      ['Enter city', 'Sandpoint'],
      ['Enter state/province', 'ID'],
      ['Enter ZIP/Postal code', '83864']
    ];
    for (const [ph, val] of fields) {
      const inp = Array.from(document.querySelectorAll('input')).find(el => el.placeholder === ph);
      if (inp && inp.value !== val) {
        setter.call(inp, val);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    // Verify all fields
    const all = {};
    Array.from(document.querySelectorAll('input')).filter(el => el.offsetParent !== null).forEach(inp => {
      all[inp.placeholder || inp.type] = inp.value;
    });
    return JSON.stringify(all);
  `);
  console.log("All fields:", r);

  // Step 3: Click Review
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review your profile') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
  const reviewBtn = JSON.parse(r);
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked Review");
    await sleep(3000);

    // Step 4: Phone verification dialog should appear - fill in the phone and click Send code
    r = await eval_(`
      const dialog = document.body.innerText.includes('verify your phone');
      const sendCodeBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Send code' && b.offsetParent !== null);
      const dialogPhone = Array.from(document.querySelectorAll('input[type="tel"]'))
        .filter(el => el.offsetParent !== null);
      return JSON.stringify({
        hasDialog: dialog,
        hasSendCode: !!sendCodeBtn,
        phoneInputs: dialogPhone.map(el => ({ value: el.value, placeholder: el.placeholder }))
      });
    `);
    console.log("Verification dialog:", r);
    const dialogState = JSON.parse(r);

    if (dialogState.hasDialog && dialogState.hasSendCode) {
      // Set the phone in the dialog input
      r = await eval_(`
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        const phoneInputs = Array.from(document.querySelectorAll('input[type="tel"]'))
          .filter(el => el.offsetParent !== null);
        // The dialog phone input is typically the last one
        const dialogPhone = phoneInputs[phoneInputs.length - 1];
        if (dialogPhone) {
          setter.call(dialogPhone, '7865879726');
          dialogPhone.dispatchEvent(new Event('input', { bubbles: true }));
          dialogPhone.dispatchEvent(new Event('change', { bubbles: true }));
          return 'dialog phone set: ' + dialogPhone.value;
        }
        return 'no dialog phone';
      `);
      console.log(r);
      await sleep(500);

      // Click Send code
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Send code' && b.offsetParent !== null);
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      const sendBtn = JSON.parse(r);
      if (!sendBtn.error) {
        await clickAt(send, sendBtn.x, sendBtn.y);
        console.log("Clicked Send code - check your phone for verification code!");
        await sleep(5000);

        // Check what's next
        r = await eval_(`
          return JSON.stringify({
            body: document.body.innerText.substring(0, 500),
            inputs: Array.from(document.querySelectorAll('input'))
              .filter(el => el.offsetParent !== null)
              .map(el => ({ type: el.type, placeholder: el.placeholder || '', value: el.value }))
          });
        `);
        console.log("\nAfter Send code:", r);
      }
    }
  }

  ws.close();
  console.log("\n*** Check your phone (786-587-9726) for the verification code! ***");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
