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

  // Find ALL checkboxes on the page
  let r = await eval_(`
    const cbs = document.querySelectorAll('input[type="checkbox"]');
    return JSON.stringify(Array.from(cbs).map(cb => ({
      name: cb.name,
      id: cb.id,
      checked: cb.checked,
      value: cb.value,
      visible: cb.offsetParent !== null,
      label: cb.closest('label')?.textContent?.trim().substring(0, 80) || cb.parentElement?.textContent?.trim().substring(0, 80) || 'no label'
    })));
  `);
  console.log("All checkboxes:", r);

  // Check and fix age checkbox
  r = await eval_(`
    const cb = document.querySelector('#user_agreements_is_full_age');
    if (!cb) return 'age checkbox not found';
    if (!cb.checked) {
      // Try setting checked directly AND dispatching events
      cb.checked = true;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
      cb.dispatchEvent(new Event('click', { bubbles: true }));
    }
    return 'age checked: ' + cb.checked;
  `);
  console.log("Age fix:", r);

  // Find and check the T&C checkbox (ID might be different)
  r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
    const tcCb = cbs.find(cb => cb.name.includes('general') || cb.name.includes('agreements'));
    if (!tcCb) {
      // Look broader
      const allCbs = cbs.filter(cb => cb.name.includes('agreement'));
      return 'T&C not found. Agreement checkboxes: ' + JSON.stringify(allCbs.map(c => ({ name: c.name, id: c.id })));
    }
    if (!tcCb.checked) {
      tcCb.checked = true;
      tcCb.dispatchEvent(new Event('change', { bubbles: true }));
      tcCb.dispatchEvent(new Event('click', { bubbles: true }));
    }
    return 'T&C (' + tcCb.id + ') checked: ' + tcCb.checked;
  `);
  console.log("T&C fix:", r);

  // Now try to check all agreement checkboxes that aren't checked
  r = await eval_(`
    const cbs = document.querySelectorAll('input[type="checkbox"][name*="agreement"]');
    const results = [];
    cbs.forEach(cb => {
      if (!cb.checked) {
        cb.checked = true;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
        results.push('checked: ' + cb.id);
      } else {
        results.push('already: ' + cb.id);
      }
    });
    return JSON.stringify(results);
  `);
  console.log("All agreements:", r);
  await sleep(200);

  // Now try Continue again
  await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) contentDiv.style.overflow = 'auto';
  `);

  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.trim() === 'Continue');
    // Find the step 2 Continue (should be second one, or the visible one)
    for (const btn of btns) {
      btn.scrollIntoView({ block: 'center' });
      await new Promise(r => setTimeout(r, 200));
      const rect = btn.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
      }
    }
    return 'none visible';
  `);
  console.log("\nContinue:", r);

  if (r !== 'none visible') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Continue");
    await sleep(3000);

    // Check if we made it to step 3
    r = await eval_(`
      const submit = document.querySelector('input[type="submit"]');
      const mobileCb = document.querySelector('#mobile_app_installed');
      return JSON.stringify({
        submitExists: !!submit,
        submitVisible: submit?.offsetParent !== null,
        mobileCbVisible: mobileCb?.offsetParent !== null
      });
    `);
    console.log("Step 3 check:", r);

    const step3 = JSON.parse(r);
    if (step3.mobileCbVisible || step3.submitVisible) {
      console.log("\n=== STEP 3: Submit ===");

      // Check mobile checkbox
      r = await eval_(`
        const cb = document.querySelector('#mobile_app_installed');
        if (cb && !cb.checked) { cb.checked = true; cb.dispatchEvent(new Event('change', { bubbles: true })); }
        return 'mobile: ' + cb?.checked;
      `);
      console.log("Mobile:", r);
      await sleep(100);

      // Click Finish (input[type=submit])
      r = await eval_(`
        const submit = document.querySelector('input[type="submit"]');
        if (submit) {
          submit.scrollIntoView({ block: 'center' });
          await new Promise(r => setTimeout(r, 200));
          const rect = submit.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
        }
        return 'not found';
      `);
      console.log("Finish:", r);

      if (r !== 'not found') {
        const fpos = JSON.parse(r);
        if (fpos.w > 0 && fpos.y > 0) {
          await clickAt(send, fpos.x, fpos.y);
          console.log("Clicked Finish!");
        }
      }

      await sleep(15000);

      r = await eval_(`return window.location.href`);
      console.log("\nURL:", r);
      r = await eval_(`return document.body.innerText.substring(0, 3000)`);
      console.log("\nPage:", r);
    } else {
      // Still not on step 3
      r = await eval_(`
        const errors = document.querySelectorAll('[class*="error"], .invalid-feedback');
        return JSON.stringify(Array.from(errors).filter(e => e.textContent.trim().length > 0 && e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 80)));
      `);
      console.log("Still errors:", r);
    }
  }

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
