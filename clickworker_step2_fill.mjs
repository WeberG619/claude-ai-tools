const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
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

  const setVal = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (el) {
        const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSet.call(el, '${value}');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return 'set';
      }
      return 'not found';
    `);
  };

  // Birthday
  let r = await setVal('#user_date_of_birth', '1975-06-15');
  console.log("Birthday:", r);
  await sleep(200);

  // Country - United States
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
  await sleep(200);

  // Native language - English USA
  r = await eval_(`
    const sel = document.querySelector('#user_native_languages');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text.includes('English USA')) {
        sel.options[i].selected = true;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    // Try just English
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === 'English') {
        sel.options[i].selected = true;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'not found';
  `);
  console.log("Language:", r);
  await sleep(200);

  // Street - use a general address
  r = await setVal('#user_address_street', '786 NW 5th St');
  console.log("Street:", r);
  await sleep(200);

  // Zip code
  r = await setVal('#user_address_postal_code', '33136');
  console.log("Zip:", r);
  await sleep(200);

  // City
  r = await setVal('#user_address_city', 'Miami');
  console.log("City:", r);
  await sleep(200);

  // Phone code - US +1
  r = await eval_(`
    const sel = document.querySelector('#user_address_phone_code');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === '+1' || sel.options[i].value === '+1') {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text;
      }
    }
    return 'not found';
  `);
  console.log("Phone code:", r);
  await sleep(200);

  // Phone number
  r = await setVal('#user_address_phone_number', '7865879726');
  console.log("Phone:", r);
  await sleep(200);

  // Age checkbox
  r = await eval_(`
    const cb = document.querySelector('#user_agreements_is_full_age');
    if (cb && !cb.checked) {
      cb.click();
      return 'checked';
    }
    return cb ? 'already checked' : 'not found';
  `);
  console.log("Age checkbox:", r);
  await sleep(300);

  // Verify all fields
  r = await eval_(`
    return JSON.stringify({
      birthday: document.querySelector('#user_date_of_birth')?.value,
      country: document.querySelector('#user_address_country')?.options[document.querySelector('#user_address_country')?.selectedIndex]?.text,
      language: Array.from(document.querySelector('#user_native_languages')?.selectedOptions || []).map(o => o.text).join(', '),
      street: document.querySelector('#user_address_street')?.value,
      zip: document.querySelector('#user_address_postal_code')?.value,
      city: document.querySelector('#user_address_city')?.value,
      phoneCode: document.querySelector('#user_address_phone_code')?.options[document.querySelector('#user_address_phone_code')?.selectedIndex]?.text,
      phone: document.querySelector('#user_address_phone_number')?.value,
      ageChecked: document.querySelector('#user_agreements_is_full_age')?.checked
    });
  `);
  console.log("\nAll fields:", r);

  // Click Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("\nContinue:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Continue");
    await sleep(10000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 4000)`);
    console.log("\nPage:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
