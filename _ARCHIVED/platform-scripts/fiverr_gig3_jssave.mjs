// Try saving gig #3 overview via JS button click
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

  // Check current form state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      title: document.querySelector('textarea')?.value?.substring(0, 60) || '',
      categoryVals: Array.from(document.querySelectorAll('[class*="single-value"]'))
        .filter(el => el.offsetParent !== null).map(el => el.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag-name'))
        .map(el => el.textContent.trim()),
      langCount: document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/)?.[0] || 'not found'
    });
  `);
  console.log("State:", r);

  // First scroll to Save button area
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (saveBtn) {
      saveBtn.scrollIntoView({ block: 'center' });
      return JSON.stringify({
        text: saveBtn.textContent.trim(),
        type: saveBtn.type,
        disabled: saveBtn.disabled,
        class: (saveBtn.className || '').substring(0, 80),
        x: Math.round(saveBtn.getBoundingClientRect().x + saveBtn.getBoundingClientRect().width/2),
        y: Math.round(saveBtn.getBoundingClientRect().y + saveBtn.getBoundingClientRect().height/2),
        w: Math.round(saveBtn.getBoundingClientRect().width),
        h: Math.round(saveBtn.getBoundingClientRect().height)
      });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Save button details:", r);
  const saveDetails = JSON.parse(r);
  await sleep(500);

  if (!saveDetails.error) {
    // Method 1: Try the form submit approach
    console.log("\n=== Method 1: Form submit ===");
    r = await eval_(`
      const form = document.querySelector('form');
      if (form) {
        return JSON.stringify({ found: true, action: form.action, method: form.method, id: form.id, class: (form.className || '').substring(0, 40) });
      }
      return JSON.stringify({ found: false });
    `);
    console.log("Form:", r);

    // Method 2: Try React onClick
    console.log("\n=== Method 2: React onClick ===");
    r = await eval_(`
      const saveBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (!saveBtn) return 'no button';

      // Find React fiber
      const fiberKey = Object.keys(saveBtn).find(k => k.startsWith('__reactInternalInstance') || k.startsWith('__reactFiber'));
      if (!fiberKey) return 'no fiber';

      let fiber = saveBtn[fiberKey];
      let maxDepth = 20;
      let handlers = [];
      while (fiber && maxDepth-- > 0) {
        const props = fiber.memoizedProps || {};
        if (props.onClick) handlers.push({ depth: 20 - maxDepth, type: 'onClick' });
        if (props.onSubmit) handlers.push({ depth: 20 - maxDepth, type: 'onSubmit' });
        fiber = fiber.return;
      }
      return JSON.stringify({ fiberKey, handlers });
    `);
    console.log("React fiber:", r);

    // Method 3: CDP click on the exact center of the button
    console.log("\n=== Method 3: CDP click ===");
    // Get fresh coordinates
    r = await eval_(`
      const saveBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (saveBtn) {
        const rect = saveBtn.getBoundingClientRect();
        return JSON.stringify({
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
      return JSON.stringify({ error: 'no button' });
    `);
    const freshPos = JSON.parse(r);
    console.log("Fresh button position:", r);

    if (!freshPos.error) {
      console.log(`Clicking at (${freshPos.x}, ${freshPos.y})`);
      await clickAt(send, freshPos.x, freshPos.y);
      console.log("Clicked. Waiting 3 seconds...");
      await sleep(3000);

      // Check state
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard')
        });
      `);
      console.log("After CDP click:", r);

      // Wait more
      await sleep(5000);
      r = await eval_(`
        const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100));
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard'),
          errors,
          bodySnippet: document.body?.innerText?.substring(0, 200)
        });
      `);
      console.log("After 8s total:", r);
    }

    // If still wizard=0, try Method 4: JS click with React synthetic event
    const finalState = JSON.parse(r);
    if (finalState.wizard === '0') {
      console.log("\n=== Method 4: dispatchEvent on button ===");
      r = await eval_(`
        const saveBtn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Save & Continue');
        if (saveBtn) {
          const opts = { bubbles: true, cancelable: true, view: window };
          saveBtn.dispatchEvent(new MouseEvent('mousedown', opts));
          saveBtn.dispatchEvent(new MouseEvent('mouseup', opts));
          saveBtn.dispatchEvent(new MouseEvent('click', opts));
          return 'dispatched events';
        }
        return 'no button';
      `);
      console.log("Method 4:", r);
      await sleep(8000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard'),
          bodySnippet: document.body?.innerText?.substring(0, 200)
        });
      `);
      console.log("After Method 4:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
