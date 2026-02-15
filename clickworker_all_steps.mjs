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

  const setVal = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (el) {
        const proto = el.tagName === 'INPUT' ? window.HTMLInputElement.prototype :
                      el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype :
                      window.HTMLInputElement.prototype;
        const nativeSet = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
        if (nativeSet) nativeSet.call(el, '${value}');
        else el.value = '${value}';
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return 'set';
      }
      return 'not found';
    `);
  };

  const selectByText = async (selector, text) => {
    return await eval_(`
      const sel = document.querySelector('${selector}');
      if (!sel) return 'not found';
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].text === '${text}' || sel.options[i].text.includes('${text}')) {
          sel.selectedIndex = i;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set: ' + sel.options[i].text;
        }
      }
      return 'option not found';
    `);
  };

  console.log("=== STEP 1: Account Info ===");

  // Check if fields are pre-filled
  let r = await eval_(`return document.querySelector('#user_first_name')?.value || 'empty'`);
  console.log("First name current:", r);

  // Gender
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    if (sel) { sel.value = 'm'; sel.dispatchEvent(new Event('change', { bubbles: true })); return 'set male'; }
    return 'not found';
  `);
  console.log("Gender:", r);
  await sleep(100);

  // Name fields
  r = await setVal('#user_first_name', 'Weber');
  console.log("First:", r);
  r = await setVal('#user_last_name', 'Gouin');
  console.log("Last:", r);
  r = await setVal('#user_username', 'weberg619');
  console.log("Username:", r);
  r = await setVal('#user_email', 'weberg619@gmail.com');
  console.log("Email:", r);
  await sleep(100);

  // Password - need to use the native setter
  r = await eval_(`
    const pw = document.querySelector('#user_password');
    const pwc = document.querySelector('#user_password_confirmation');
    if (pw && pwc) {
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      set.call(pw, 'Weber@619.1974');
      pw.dispatchEvent(new Event('input', { bubbles: true }));
      pw.dispatchEvent(new Event('change', { bubbles: true }));
      set.call(pwc, 'Weber@619.1974');
      pwc.dispatchEvent(new Event('input', { bubbles: true }));
      pwc.dispatchEvent(new Event('change', { bubbles: true }));
      return 'passwords set';
    }
    return 'not found';
  `);
  console.log("Password:", r);
  await sleep(200);

  // Fix overflow so Continue button is accessible
  r = await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) contentDiv.style.overflow = 'auto';
    return 'overflow fixed';
  `);

  // Find and click Continue on Step 1
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    const continueBtn = btns.find(b => b.textContent.trim() === 'Continue' && b.offsetParent !== null);
    if (!continueBtn) {
      // Try finding any visible Continue
      const allContinue = btns.filter(b => b.textContent.trim() === 'Continue');
      if (allContinue.length > 0) {
        allContinue[0].scrollIntoView({ block: 'center' });
        await new Promise(r => setTimeout(r, 300));
        const rect = allContinue[0].getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
      }
      return 'not found';
    }
    continueBtn.scrollIntoView({ block: 'center' });
    await new Promise(r => setTimeout(r, 300));
    const rect = continueBtn.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
  `);
  console.log("\nStep 1 Continue:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (pos.w > 0 && pos.y > 0) {
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Continue");
    } else {
      // JS click fallback
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Continue');
        if (btn) { btn.click(); return 'js clicked'; }
        return 'not found';
      `);
      console.log("JS click:", r);
    }
  }

  await sleep(3000);

  // Verify we moved to step 2
  r = await eval_(`
    const active = document.querySelector('.nav-link.active');
    return active?.textContent?.trim().substring(0, 20) || 'unknown';
  `);
  console.log("\nActive step:", r);

  // Check for validation errors on step 1
  r = await eval_(`
    const errors = document.querySelectorAll('[class*="error"], .field_with_errors, .invalid-feedback');
    return JSON.stringify(Array.from(errors).filter(e => e.textContent.trim().length > 0 && e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 80)));
  `);
  console.log("Step 1 errors:", r);

  // Check if birthday field is visible (step 2 indicator)
  r = await eval_(`
    const bday = document.querySelector('#user_date_of_birth');
    return bday ? 'birthday field found, visible: ' + (bday.offsetParent !== null) : 'no birthday field';
  `);
  console.log("Birthday check:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved after Step 1");

  ws.close();
})().catch(e => console.error("Error:", e.message));
