// Debug: check offer packages toggle, fix React price state
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

  // Step 1: Check the "Offer packages" toggle/checkbox
  console.log("=== Step 1: Check 'Offer packages' toggle ===");
  const toggleInfo = await eval_(`
    (function() {
      // Look for "Offer packages" near a toggle/switch/checkbox
      const body = document.body.innerText;
      const offerIdx = body.indexOf('Offer packages');

      // Find checkbox near "Offer packages"
      const allLabels = Array.from(document.querySelectorAll('label'));
      const offerLabel = allLabels.find(l => l.textContent.includes('Offer packages'));

      // Find all toggle switches
      const toggles = Array.from(document.querySelectorAll('[class*="toggle"], [class*="switch"], [role="switch"]'));

      // Find the packages checkbox (the one near "Offer packages" text)
      const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
      const pkgCheckbox = cbs.find(cb => {
        const parent = cb.closest('div, label, section');
        return parent?.textContent?.includes('Offer packages') || parent?.textContent?.includes('offer packages');
      });

      return JSON.stringify({
        offerInText: offerIdx >= 0,
        offerLabel: offerLabel?.textContent?.trim()?.substring(0, 40) || 'not found',
        toggleCount: toggles.length,
        toggleTexts: toggles.map(t => t.textContent?.trim()?.substring(0, 30) || t.className?.substring(0, 30)),
        pkgCheckbox: pkgCheckbox ? {
          checked: pkgCheckbox.checked,
          rect: (() => {
            const label = pkgCheckbox.closest('label') || pkgCheckbox.parentElement;
            const rect = label.getBoundingClientRect();
            return { x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) };
          })()
        } : null,
        // Also look for any disabled/inactive pricing section
        pricingDisabled: !!document.querySelector('[class*="pricing"][class*="disabled"]') || !!document.querySelector('[class*="package"][class*="disabled"]')
      });
    })()
  `);
  console.log("Toggle info:", toggleInfo);

  const toggleData = JSON.parse(toggleInfo);
  if (toggleData.pkgCheckbox && !toggleData.pkgCheckbox.checked) {
    console.log("Offer packages toggle is OFF! Clicking to enable...");
    await cdpClick(toggleData.pkgCheckbox.rect.x, toggleData.pkgCheckbox.rect.y);
    await sleep(1500);
  }

  // Step 2: Scroll up and take a full page scan
  console.log("\n=== Step 2: Full page scan ===");
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  const fullScan = await eval_(`
    (function() {
      const sections = [];
      let y = 0;
      const step = 200;

      // Map all visible text and elements from top to bottom
      const allElements = Array.from(document.querySelectorAll('*')).filter(el => {
        const rect = el.getBoundingClientRect();
        return rect.width > 100 && rect.height > 10 && rect.height < 80 && el.children.length === 0;
      });

      return JSON.stringify({
        pageHeight: document.body.scrollHeight,
        textMap: allElements.slice(0, 50).map(el => {
          const rect = el.getBoundingClientRect();
          return {
            text: el.textContent.trim().substring(0, 40),
            tag: el.tagName,
            y: Math.round(rect.y),
            class: el.className?.substring?.(0, 20) || ''
          };
        }).filter(i => i.text.length > 0)
      });
    })()
  `);
  console.log("Page map:", fullScan);

  // Step 3: Try using React fiber to update prices
  console.log("\n=== Step 3: React fiber price update ===");
  const reactPrices = await eval_(`
    (function() {
      const priceInputs = Array.from(document.querySelectorAll('.price-input, input[type="number"]'));
      const results = [];

      for (const input of priceInputs) {
        let fiber = null;
        for (const key of Object.keys(input)) {
          if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
            fiber = input[key];
            break;
          }
        }
        if (!fiber) { results.push('no fiber for ' + input.value); continue; }

        // Walk up to find onChange
        let current = fiber;
        let found = false;
        for (let d = 0; d < 20; d++) {
          const props = current?.memoizedProps;
          if (props?.onChange) {
            // Found the onChange handler
            const event = { target: { value: input.value }, currentTarget: { value: input.value } };
            try {
              props.onChange(event);
              results.push('triggered onChange for $' + input.value + ' at depth ' + d);
              found = true;
            } catch(e) {
              results.push('onChange error: ' + e.message);
            }
            break;
          }
          current = current?.return;
        }
        if (!found) results.push('no onChange found for $' + input.value);
      }
      return JSON.stringify(results);
    })()
  `);
  console.log("React price update:", reactPrices);
  await sleep(1000);

  // Step 4: Try just clicking "Save" (not "Save & Preview") - maybe it works differently
  console.log("\n=== Step 4: Try Save button ===");
  const saveResult = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      return JSON.stringify(btns.filter(b => b.offsetParent !== null).map(b => ({
        text: b.textContent.trim(),
        class: b.className?.substring?.(0, 30) || '',
        disabled: b.disabled
      })).filter(b => b.text.length > 0 && b.text.length < 30));
    })()
  `);
  console.log("All buttons:", saveResult);

  // Click "Save" (the simpler one, not "Save & Preview")
  await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      const saveBtn = btns.find(b => b.textContent.trim() === 'Save' && b.offsetParent);
      if (saveBtn) saveBtn.click();
    })()
  `);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      step: new URLSearchParams(window.location.search).get('step'),
      toasts: document.querySelector('[class*="toast"], [class*="Toast"], [class*="notification"]')?.textContent?.trim()?.substring(0, 100) || 'none',
      errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0 && !t.includes('accessibility')).slice(0, 5)
    })
  `);
  console.log("After Save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
