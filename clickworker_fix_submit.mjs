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

  // 1. Fix State to Florida
  let r = await eval_(`
    const sel = document.querySelector('#user_address_state');
    if (!sel) return 'state field not found';
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === 'Florida' || sel.options[i].value === 'FL') {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return 'Set: ' + sel.options[i].text + ' (value: ' + sel.options[i].value + ')';
      }
    }
    return 'Florida not found in options';
  `);
  console.log("State:", r);
  await sleep(200);

  // 2. Check T&C checkbox
  r = await eval_(`
    const cb = document.querySelector('#user_agreements_general_5908');
    if (cb && !cb.checked) {
      cb.click();
      return 'checked: ' + cb.checked;
    }
    return cb ? 'already checked' : 'not found';
  `);
  console.log("T&C checkbox:", r);
  await sleep(300);

  // Verify all fields one more time
  r = await eval_(`
    return JSON.stringify({
      birthday: document.querySelector('#user_date_of_birth')?.value,
      country: document.querySelector('#user_address_country')?.options[document.querySelector('#user_address_country')?.selectedIndex]?.text,
      state: document.querySelector('#user_address_state')?.options[document.querySelector('#user_address_state')?.selectedIndex]?.text,
      street: document.querySelector('#user_address_street')?.value,
      zip: document.querySelector('#user_address_postal_code')?.value,
      city: document.querySelector('#user_address_city')?.value,
      phone: document.querySelector('#user_address_phone_number')?.value,
      ageChecked: document.querySelector('#user_agreements_is_full_age')?.checked,
      tcChecked: document.querySelector('#user_agreements_general_5908')?.checked
    });
  `);
  console.log("\nAll fields:", r);

  // 3. Make the overflow scrollable and scroll to Continue button
  r = await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) {
      contentDiv.style.overflow = 'auto';
    }
    const btn = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null)
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      btn.scrollIntoView({ block: 'center', behavior: 'instant' });
      await new Promise(r => setTimeout(r, 500));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) });
    }
    return 'not found';
  `);
  console.log("\nContinue button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (pos.w > 0 && pos.h > 0 && pos.y > 0 && pos.y < 1200) {
      await clickAt(send, pos.x, pos.y);
      console.log("CDP clicked Continue at", pos.x, pos.y);
    } else {
      // Use JS click as fallback
      console.log("Button not in viewport (pos:", pos, "), trying JS click");
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .filter(b => b.offsetParent !== null)
          .find(b => b.textContent.trim() === 'Continue');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not found';
      `);
      console.log("JS click:", r);
    }

    await sleep(8000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);

    // Check validation errors
    r = await eval_(`
      const els = document.querySelectorAll('[class*="error"], [class*="alert"], .help-block, .field_with_errors');
      return JSON.stringify(Array.from(els).filter(e => e.offsetParent !== null && e.textContent.trim().length > 0).map(e => e.textContent.trim().substring(0, 100)));
    `);
    console.log("\nErrors:", r);

    // Check for step 3 indicators
    r = await eval_(`
      const checkboxes = document.querySelectorAll('input[type="checkbox"]');
      return JSON.stringify(Array.from(checkboxes).map(cb => ({
        name: cb.name, id: cb.id, checked: cb.checked,
        label: cb.closest('label')?.textContent?.trim().substring(0, 80) || cb.parentElement?.textContent?.trim().substring(0, 80) || '',
        visible: cb.offsetParent !== null
      })));
    `);
    console.log("\nCheckboxes:", r);
  }

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
