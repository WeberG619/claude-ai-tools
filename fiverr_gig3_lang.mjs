// Fix gig #3 Language metadata - click the actual checkbox for English
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // First make sure we're on Language tab and scroll there
  let r = await eval_(`
    // Scroll to metadata and click Language tab
    const metaSection = document.querySelector('[class*="metadata-names"]');
    if (metaSection) metaSection.scrollIntoView({ block: 'start' });
    return 'scrolled';
  `);
  await sleep(500);

  // Click Language tab
  r = await eval_(`
    const langTab = Array.from(document.querySelectorAll('li'))
      .find(el => el.textContent.trim() === 'Language');
    if (langTab) {
      langTab.scrollIntoView({ block: 'center' });
      const rect = langTab.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no tab' });
  `);
  const langTabPos = JSON.parse(r);
  if (!langTabPos.error) {
    await clickAt(send, langTabPos.x, langTabPos.y);
    await sleep(500);
  }

  // Now find the English checkbox specifically
  r = await eval_(`
    const engLi = Array.from(document.querySelectorAll('li.option'))
      .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
    if (engLi) {
      const checkbox = engLi.querySelector('input[type="checkbox"]');
      if (checkbox) {
        checkbox.scrollIntoView({ block: 'center' });
        const rect = checkbox.getBoundingClientRect();
        return JSON.stringify({
          checkbox: { x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), checked: checkbox.checked },
          liRect: (function() { const r = engLi.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
        });
      }
      // No checkbox, return LI position
      const rect = engLi.getBoundingClientRect();
      return JSON.stringify({ noCheckbox: true, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no English option' });
  `);
  console.log("English checkbox details:", r);
  const engDetails = JSON.parse(r);

  // Try approach 1: Click the checkbox directly via CDP
  if (engDetails.checkbox) {
    console.log(`Clicking checkbox at (${engDetails.checkbox.x}, ${engDetails.checkbox.y}), checked=${engDetails.checkbox.checked}`);
    await clickAt(send, engDetails.checkbox.x, engDetails.checkbox.y);
    await sleep(1000);
  }

  // Check result
  r = await eval_(`
    const engLi = Array.from(document.querySelectorAll('li.option'))
      .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
    const checkbox = engLi?.querySelector('input[type="checkbox"]');
    const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
    return JSON.stringify({
      checked: checkbox?.checked,
      count: countMatch?.[0],
      liClass: engLi?.className
    });
  `);
  console.log("After checkbox click:", r);
  let state = JSON.parse(r);

  // If still not working, try approach 2: use DOM.setAttributeValue or check the checkbox directly
  if (state.count === '0 / 3') {
    console.log("\nCheckbox click didn't register. Trying direct state manipulation...");

    // Try setting checked via JS and dispatching change event
    r = await eval_(`
      const engLi = Array.from(document.querySelectorAll('li.option'))
        .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
      const checkbox = engLi?.querySelector('input[type="checkbox"]');
      if (checkbox) {
        // Try React's native input setter
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'checked').set;
        nativeInputValueSetter.call(checkbox, true);
        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        checkbox.dispatchEvent(new Event('click', { bubbles: true }));
        return 'set checked via native setter + dispatched events';
      }
      return 'no checkbox found';
    `);
    console.log("Native setter:", r);
    await sleep(1000);

    r = await eval_(`
      const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
      return countMatch?.[0] || 'not found';
    `);
    console.log("Count after native setter:", r);
  }

  // If still not working, try approach 3: Find and call the React onChange handler
  state = JSON.parse(await eval_(`
    const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
    return JSON.stringify({ count: countMatch?.[0] });
  `));

  if (state.count === '0 / 3') {
    console.log("\nTrying approach 3: React fiber...");

    r = await eval_(`
      const engLi = Array.from(document.querySelectorAll('li.option'))
        .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
      if (!engLi) return 'no English LI';

      // Find React fiber
      const fiberKey = Object.keys(engLi).find(k => k.startsWith('__reactInternalInstance') || k.startsWith('__reactFiber'));
      if (!fiberKey) return 'no React fiber on LI';

      let fiber = engLi[fiberKey];
      let handlers = [];
      let maxDepth = 30;
      while (fiber && maxDepth-- > 0) {
        const props = fiber.memoizedProps || fiber.pendingProps || {};
        if (props.onClick) handlers.push({ type: 'onClick', depth: 30 - maxDepth });
        if (props.onChange) handlers.push({ type: 'onChange', depth: 30 - maxDepth });
        if (props.onSelect) handlers.push({ type: 'onSelect', depth: 30 - maxDepth });
        fiber = fiber.return;
      }
      return JSON.stringify({ fiberKey, handlers });
    `);
    console.log("React fiber handlers:", r);

    // Try triggering the React onClick handler
    r = await eval_(`
      const engLi = Array.from(document.querySelectorAll('li.option'))
        .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
      if (!engLi) return 'no LI';

      const fiberKey = Object.keys(engLi).find(k => k.startsWith('__reactInternalInstance') || k.startsWith('__reactFiber'));
      if (!fiberKey) return 'no fiber';

      let fiber = engLi[fiberKey];
      let maxDepth = 30;
      while (fiber && maxDepth-- > 0) {
        const props = fiber.memoizedProps || fiber.pendingProps || {};
        if (props.onClick) {
          try {
            props.onClick({ target: engLi, currentTarget: engLi, preventDefault: ()=>{}, stopPropagation: ()=>{} });
            return 'called onClick at depth ' + (30 - maxDepth);
          } catch(e) {
            return 'onClick error: ' + e.message;
          }
        }
        fiber = fiber.return;
      }
      return 'no onClick found';
    `);
    console.log("React onClick result:", r);
    await sleep(1000);

    r = await eval_(`
      const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
      return countMatch?.[0] || 'not found';
    `);
    console.log("Count after React onClick:", r);
  }

  // === SAVE ===
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
    await sleep(8000);

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
