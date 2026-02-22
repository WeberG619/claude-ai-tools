const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No tab"); return; }

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

  // Helper to set input value using native setter
  const setInput = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (!el) return 'not found: ${selector}';
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(el, '${value}');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set ' + el.name + ' = ' + el.value;
    `);
  };

  // Helper to set select value
  const setSelect = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (!el) return 'not found: ${selector}';
      el.value = '${value}';
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set ' + el.name + ' = ' + el.value;
    `);
  };

  // Make sure we're on the edit page
  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  if (!r.includes('contact_details/edit')) {
    await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/contact_details/edit" });
    await sleep(4000);
    r = await eval_(`return window.location.href`);
    console.log("Navigated to:", r);
  }

  // Update Birthday: March 18, 1974
  // Month = 3 (March)
  r = await setSelect('#user_date_of_birth_2i', '3');
  console.log("Month:", r);

  // Day = 18
  r = await setSelect('#user_date_of_birth_3i', '18');
  console.log("Day:", r);

  // Year = 1974
  r = await setSelect('#user_date_of_birth_1i', '1974');
  console.log("Year:", r);

  // Update Address: 619 Hopkins Road, Sandpoint, ID 83864
  r = await setInput('#user_primary_address_attributes_street', '619 Hopkins Road');
  console.log("Street:", r);

  r = await setInput('#user_primary_address_attributes_city', 'Sandpoint');
  console.log("City:", r);

  // State = ID (Idaho)
  r = await setSelect('#user_primary_address_attributes_state', 'ID');
  console.log("State:", r);

  r = await setInput('#user_primary_address_attributes_postal_code', '83864');
  console.log("ZIP:", r);

  await sleep(500);

  // Verify all values before submitting
  r = await eval_(`
    return JSON.stringify({
      month: document.querySelector('#user_date_of_birth_2i').value,
      day: document.querySelector('#user_date_of_birth_3i').value,
      year: document.querySelector('#user_date_of_birth_1i').value,
      street: document.querySelector('#user_primary_address_attributes_street').value,
      city: document.querySelector('#user_primary_address_attributes_city').value,
      state: document.querySelector('#user_primary_address_attributes_state').value,
      zip: document.querySelector('#user_primary_address_attributes_postal_code').value,
      country: document.querySelector('#user_primary_address_attributes_country').value
    });
  `);
  console.log("\nVerification:", r);

  // Click Save button
  r = await eval_(`
    const btn = document.querySelector('input[type="submit"][value="Save"]');
    if (btn) { btn.click(); return 'clicked Save'; }
    return 'Save button not found';
  `);
  console.log("\nSave:", r);
  await sleep(4000);

  // Check result
  r = await eval_(`return window.location.href`);
  console.log("\nURL after save:", r);
  r = await eval_(`return document.body.innerText.substring(0, 2000)`);
  console.log("\nPage after save:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
