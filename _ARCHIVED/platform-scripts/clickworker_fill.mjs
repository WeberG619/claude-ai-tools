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

  // Helper to set input values
  const setField = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (el) {
        const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSet.call(el, '${value}');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'set: ' + el.value;
      }
      return 'not found';
    `);
  };

  // Fill Gender - select "Male"
  let r = await eval_(`
    const sel = document.querySelector('#user_gender');
    if (sel) {
      sel.value = 'male';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set: ' + sel.value;
    }
    return 'not found';
  `);
  console.log("Gender:", r);
  await sleep(200);

  // Fill First Name
  r = await setField('#user_first_name', 'Weber');
  console.log("First Name:", r);
  await sleep(200);

  // Fill Last Name
  r = await setField('#user_last_name', 'Gouin');
  console.log("Last Name:", r);
  await sleep(200);

  // Fill Username
  r = await setField('#user_username', 'weberg619');
  console.log("Username:", r);
  await sleep(200);

  // Fill Email
  r = await setField('#user_email', 'weberg619@gmail.com');
  console.log("Email:", r);
  await sleep(200);

  // Check what the form looks like now
  r = await eval_(`
    const fields = ['#user_gender', '#user_first_name', '#user_last_name', '#user_username', '#user_email'];
    return JSON.stringify(fields.map(sel => {
      const el = document.querySelector(sel);
      return { field: sel, value: el?.value || 'N/A' };
    }));
  `);
  console.log("\nFilled fields:", r);

  // Check for CAPTCHA type
  r = await eval_(`
    const captcha = document.querySelector('.g-recaptcha, [class*="recaptcha"], iframe[src*="recaptcha"]');
    if (captcha) {
      const rect = captcha.getBoundingClientRect();
      return JSON.stringify({
        tag: captcha.tagName,
        classes: (typeof captcha.className === 'string' ? captcha.className : '').substring(0, 60),
        src: captcha.src?.substring(0, 80) || '',
        visible: rect.width > 0 && rect.height > 0,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    // Check for invisible recaptcha
    const badge = document.querySelector('.grecaptcha-badge');
    if (badge) return 'invisible recaptcha (badge found)';
    return 'no captcha element found';
  `);
  console.log("\nCAPTCHA:", r);

  // Password fields - leave for user
  console.log("\n** Password fields left empty - Weber needs to set a password **");

  // Check Continue button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, input[type="submit"]'))
      .find(b => b.textContent?.includes('Continue') || b.value?.includes('Continue'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent?.trim() || btn.value, disabled: btn.disabled, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Continue button:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
