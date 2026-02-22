// Fix gig #3 subcategory - use keyboard to select from dropdown
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
  // Full mouse event sequence: move, down, up
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Get current state
  let r = await eval_(`
    return JSON.stringify({
      categoryValues: Array.from(document.querySelectorAll('[class*="single-value"]'))
        .filter(el => el.offsetParent !== null).map(el => el.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag-name'))
        .map(el => el.textContent.trim()),
      placeholders: Array.from(document.querySelectorAll('[class*="placeholder"]'))
        .filter(el => el.offsetParent !== null).map(el => el.textContent.trim())
    });
  `);
  console.log("State:", r);

  // === APPROACH 1: Click subcategory dropdown and type to filter ===
  console.log("\n=== Subcategory - Type to filter ===");

  // Click the subcategory control
  r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="category-selector__control"]'))
      .filter(el => el.offsetParent !== null && !el.parentElement?.closest('[class*="category-selector__control"]'));
    const sub = controls[1];
    if (sub) {
      sub.scrollIntoView({ block: 'center' });
      const rect = sub.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: sub.textContent.trim().substring(0, 40) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Subcategory control:", r);
  const subCtrl = JSON.parse(r);

  if (!subCtrl.error) {
    await clickAt(send, subCtrl.x, subCtrl.y);
    await sleep(1000);

    // Check if dropdown opened - look for an input that appeared
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
        .map(el => ({
          id: el.id,
          class: (el.className || '').substring(0, 50),
          placeholder: el.placeholder,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          focused: document.activeElement === el
        }));
      return JSON.stringify(inputs);
    `);
    console.log("Visible inputs:", r);

    // Type "Resume" to filter the dropdown
    await send("Input.insertText", { text: "Resume" });
    await sleep(1000);

    // Check filtered options
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && el.getBoundingClientRect().height > 5)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          id: el.id || ''
        }));
      return JSON.stringify(opts);
    `);
    console.log("Filtered options:", r);
    const filteredOpts = JSON.parse(r);

    if (filteredOpts.length > 0) {
      const resume = filteredOpts.find(o => o.text.includes('Resume Writing')) || filteredOpts[0];
      console.log(`Clicking option "${resume.text}" at (${resume.x}, ${resume.y})`);

      // Try mouseDown on the option element directly via JS
      r = await eval_(`
        const opt = Array.from(document.querySelectorAll('[class*="option"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().includes('Resume Writing'));
        if (opt.length > 0) {
          // Simulate full event sequence
          opt[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
          opt[0].dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
          opt[0].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
          return 'dispatched events on: ' + opt[0].textContent.trim();
        }
        return 'not found';
      `);
      console.log("JS click result:", r);
      await sleep(1500);
    } else {
      // Try Enter to select the highlighted option
      console.log("No filtered options visible, pressing Enter...");
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      await sleep(1000);
    }

    // Check if it worked
    r = await eval_(`
      return JSON.stringify({
        categoryValues: Array.from(document.querySelectorAll('[class*="single-value"]'))
          .filter(el => el.offsetParent !== null).map(el => el.textContent.trim()),
        placeholders: Array.from(document.querySelectorAll('[class*="placeholder"]'))
          .filter(el => el.offsetParent !== null).map(el => el.textContent.trim())
      });
    `);
    console.log("After attempt 1:", r);
    const state1 = JSON.parse(r);

    // If still showing placeholder, try approach 2: react-select internal API
    if (state1.placeholders.length > 0) {
      console.log("\n=== Approach 2: React internals ===");

      // Try to find and trigger the react-select onChange
      r = await eval_(`
        // Find the react-select container for subcategory
        const containers = Array.from(document.querySelectorAll('.orca-combo-box'));
        if (containers.length >= 2) {
          const subContainer = containers[1];
          // Try to find React fiber
          const key = Object.keys(subContainer).find(k => k.startsWith('__reactInternalInstance') || k.startsWith('__reactFiber'));
          if (key) {
            let fiber = subContainer[key];
            let maxDepth = 20;
            while (fiber && maxDepth-- > 0) {
              if (fiber.memoizedProps?.onChange) {
                return JSON.stringify({ found: 'onChange', fiberType: fiber.type?.toString()?.substring(0, 30) || 'unknown' });
              }
              if (fiber.memoizedProps?.onSelect) {
                return JSON.stringify({ found: 'onSelect' });
              }
              fiber = fiber.return;
            }
            return JSON.stringify({ found: 'fiber but no onChange', key });
          }
          return JSON.stringify({ found: 'no fiber key', keys: Object.keys(subContainer).filter(k => k.startsWith('__')).join(', ') });
        }
        return JSON.stringify({ found: 'no containers' });
      `);
      console.log("React internals:", r);

      // Try approach 3: Use the hidden input that react-select might have
      r = await eval_(`
        const hiddenInputs = Array.from(document.querySelectorAll('input[type="hidden"]'))
          .map(el => ({ name: el.name, value: el.value, id: el.id }));
        const selectInputs = Array.from(document.querySelectorAll('select'))
          .map(el => ({
            name: el.name, value: el.value, id: el.id,
            options: Array.from(el.options).map(o => ({ value: o.value, text: o.text }))
          }));
        return JSON.stringify({ hiddenInputs, selectInputs });
      `);
      console.log("Hidden/select inputs:", r);
    }
  }

  // === SAVE ATTEMPT ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  await sleep(800);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
