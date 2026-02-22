// Enable "Offer packages" toggle and fix pricing
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit"));
  if (!tab) throw new Error("No Fiverr edit tab");
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
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 500)); return null; }
    return r.result?.value;
  };
  async function cdpClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1, buttons: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  async function tripleClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(50);
    for (let click = 1; click <= 3; click++) {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: click });
      await sleep(30);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: click });
      await sleep(30);
    }
  }
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
  async function typeText(text) {
    for (const char of text) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char, unmodifiedText: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(60);
    }
  }
  return { ws, send, eval_, cdpClick, tripleClick, pressKey, typeText };
}

async function main() {
  const { ws, send, eval_, cdpClick, tripleClick, pressKey, typeText } = await connect();

  // Step 1: Find the packages toggle
  console.log("=== Step 1: Find packages toggle ===");
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  const toggleInfo = await eval_(`
    (function() {
      // Find the pkgs-toggler element
      const toggler = document.querySelector('.pkgs-toggler') ||
                     document.querySelector('[class*="pkgs-toggler"]');
      if (toggler) {
        const rect = toggler.getBoundingClientRect();
        const input = toggler.querySelector('input[type="checkbox"]');
        return JSON.stringify({
          found: true,
          class: toggler.className,
          text: toggler.textContent.trim().substring(0, 40),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          hasCheckbox: !!input,
          checkboxChecked: input?.checked,
          html: toggler.innerHTML.substring(0, 200)
        });
      }

      // Try broader search
      const allToggles = Array.from(document.querySelectorAll('[class*="toggle"], [role="switch"]'));
      return JSON.stringify({
        found: false,
        toggles: allToggles.map(t => ({
          class: t.className.substring(0, 40),
          text: t.textContent.trim().substring(0, 30),
          rect: (() => { const r = t.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
        }))
      });
    })()
  `);
  console.log("Toggle:", toggleInfo);

  const toggle = JSON.parse(toggleInfo);
  if (toggle.found) {
    // Check if it's checked/enabled
    if (toggle.hasCheckbox && !toggle.checkboxChecked) {
      console.log("Toggle is OFF! Clicking to enable...");
      await cdpClick(toggle.x, toggle.y);
      await sleep(2000);
    } else if (!toggle.hasCheckbox) {
      // It's a custom toggle - just click it
      console.log("Custom toggle, clicking...");
      await cdpClick(toggle.x, toggle.y);
      await sleep(2000);
    } else {
      console.log("Toggle is already ON");
    }
  }

  // Step 2: Now look at what changed after toggle
  const afterToggle = await eval_(`
    JSON.stringify({
      packageHeaders: Array.from(document.querySelectorAll('th')).map(th => th.textContent.trim()),
      priceInputCount: document.querySelectorAll('.price-input, input[type="number"]').length,
      toggleState: (() => {
        const t = document.querySelector('.pkgs-toggler input[type="checkbox"]');
        return t ? t.checked : 'no checkbox';
      })()
    })
  `);
  console.log("After toggle:", afterToggle);

  // Step 3: Set prices via CDP keyboard with proper focus handling
  console.log("\n=== Step 3: Set prices ===");
  const priceInputs = await eval_(`
    (function() {
      const inputs = Array.from(document.querySelectorAll('.price-input, input[type="number"]'));
      return JSON.stringify(inputs.map(input => {
        const rect = input.getBoundingClientRect();
        return {
          value: input.value,
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          visible: rect.width > 0
        };
      }));
    })()
  `);
  console.log("Price inputs:", priceInputs);

  const priceEls = JSON.parse(priceInputs);
  const targets = ['90', '250', '500'];

  for (let i = 0; i < Math.min(priceEls.length, targets.length); i++) {
    const p = priceEls[i];
    if (!p.visible) continue;

    console.log(`\nPrice ${i+1}: $${p.value} -> $${targets[i]}`);

    // Click to focus
    await cdpClick(p.x, p.y);
    await sleep(300);

    // Select all with Ctrl+A
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 0 });
    await sleep(100);

    // Delete
    await pressKey("Backspace", "Backspace", 8);
    await sleep(200);

    // Type new value
    await typeText(targets[i]);
    await sleep(300);

    // Blur (click elsewhere to trigger validation)
    await cdpClick(p.x - 200, p.y);
    await sleep(500);
  }

  // Verify prices
  const verifyPrices = await eval_(`
    Array.from(document.querySelectorAll('.price-input, input[type="number"]')).map(i => '$' + i.value).join(', ')
  `);
  console.log("\nPrices now:", verifyPrices);

  // Step 4: Try "Save & Preview"
  console.log("\n=== Step 4: Save ===");
  await eval_(`
    Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save & Preview')?.click()
  `);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      step: new URLSearchParams(window.location.search).get('step'),
      errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0 && !t.includes('accessibility')).slice(0, 5)
    })
  `);
  console.log("After save:", afterSave);

  // If still on step 1, check the full page state
  if (afterSave.includes('"step":"1"')) {
    console.log("\nStill on step 1. Checking full form state...");
    const formState = await eval_(`
      (function() {
        // Check for any red-bordered/invalid fields
        const invalidEls = Array.from(document.querySelectorAll('.invalid, [class*="invalid"], :invalid, [aria-invalid="true"]')).filter(el => el.offsetParent !== null);

        // Check ALL form inputs for empty/invalid state
        const allInputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]), textarea, select')).filter(el => el.offsetParent !== null);
        const emptyRequired = allInputs.filter(el => !el.value && (el.required || el.getAttribute('aria-required')));

        // Check for toast/snackbar messages
        const toasts = Array.from(document.querySelectorAll('[class*="toast"], [class*="snack"], [class*="notification"], [class*="alert"]')).filter(el => el.offsetParent !== null);

        return JSON.stringify({
          invalidCount: invalidEls.length,
          invalidSample: invalidEls.slice(0, 5).map(el => ({
            tag: el.tagName,
            class: el.className?.substring?.(0, 30),
            text: el.textContent?.trim()?.substring(0, 30),
            value: el.value?.substring?.(0, 20)
          })),
          emptyRequiredCount: emptyRequired.length,
          emptyRequired: emptyRequired.map(el => ({
            tag: el.tagName,
            name: el.name,
            placeholder: el.placeholder?.substring(0, 20)
          })),
          toasts: toasts.map(t => t.textContent.trim().substring(0, 60))
        });
      })()
    `);
    console.log("Form state:", formState);

    // Also check if the "predefined options" refers to the feature checkboxes
    const featureState = await eval_(`
      (function() {
        const rows = Array.from(document.querySelectorAll('tr'));
        const features = [];
        for (const row of rows) {
          const label = row.cells?.[0]?.textContent?.trim() || '';
          const cbs = [];
          for (let i = 1; i <= 3; i++) {
            const cb = row.cells?.[i]?.querySelector('input[type="checkbox"]');
            if (cb) cbs.push({ col: i, checked: cb.checked });
          }
          if (cbs.length > 0) features.push({ label: label.substring(0, 25), cbs });
        }

        // Check delivery and revision hidden values
        const deliveryRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('delivery'));
        const revisionRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('revision'));

        return JSON.stringify({
          features,
          delivery: deliveryRow ? [1,2,3].map(i => deliveryRow.cells[i]?.querySelector('input[type="hidden"]')?.value) : null,
          revisions: revisionRow ? [1,2,3].map(i => revisionRow.cells[i]?.querySelector('input[type="hidden"]')?.value) : null
        });
      })()
    `);
    console.log("Feature state:", featureState);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
