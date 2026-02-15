const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // First check current page state
  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Get page text to understand where we are
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage text:", r);

  // Find ALL clickable elements near consent text - look for parent containers with checkbox behavior
  r = await eval_(`
    const results = [];
    // Strategy: find text nodes containing consent keywords, then walk up to find clickable containers
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const text = walker.currentNode.textContent.trim();
      if (text.includes('I confirm') || text.includes('I agree')) {
        let el = walker.currentNode.parentElement;
        // Walk up to find a clickable container (label, button, or element with onClick)
        let clickTarget = null;
        let current = el;
        for (let i = 0; i < 10 && current; i++) {
          if (current.tagName === 'LABEL' || current.getAttribute('role') === 'checkbox' ||
              current.tagName === 'BUTTON' || current.querySelector('input[type="checkbox"]')) {
            clickTarget = current;
            break;
          }
          current = current.parentElement;
        }

        // Also look for a checkbox input as sibling or nearby
        if (!clickTarget && el) {
          const parent = el.closest('div');
          if (parent) {
            const checkbox = parent.querySelector('input[type="checkbox"], [role="checkbox"], button');
            if (checkbox) clickTarget = checkbox;
          }
        }

        const target = clickTarget || el;
        if (target) {
          const rect = target.getBoundingClientRect();
          results.push({
            text: text.substring(0, 60),
            tag: target.tagName,
            role: target.getAttribute('role'),
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            w: Math.round(rect.width),
            h: Math.round(rect.height)
          });
        }
      }
    }
    return JSON.stringify(results);
  `);
  console.log("\nConsent targets:", r);

  const targets = JSON.parse(r);
  for (const t of targets) {
    // Click on the left edge where a checkbox icon typically is
    const clickX = Math.max(t.x - Math.floor(t.w/2) + 15, t.x - 200);
    await clickAt(send, clickX, t.y);
    console.log(`Clicked at (${clickX}, ${t.y}) for: ${t.text}`);
    await sleep(500);
  }

  // Also try clicking specific checkbox areas by coordinate offset from text
  // Sometimes the checkbox is a separate element to the left of text
  for (const t of targets) {
    const checkboxX = t.x - Math.floor(t.w/2) - 15; // Left of the text container
    if (checkboxX > 0) {
      await clickAt(send, checkboxX, t.y);
      console.log(`Clicked checkbox area at (${checkboxX}, ${t.y})`);
      await sleep(300);
    }
  }

  await sleep(500);

  // Check Next button state
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Next'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        disabled: btn.disabled,
        text: btn.textContent.trim(),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return 'not found';
  `);
  console.log("\nNext button:", r);

  const nextInfo = JSON.parse(r !== 'not found' ? r : '{"disabled":true}');

  if (nextInfo.disabled) {
    // Debug: find all interactive elements on page
    r = await eval_(`
      const els = document.querySelectorAll('button, input, [role="checkbox"], [role="switch"], label, [tabindex]');
      return JSON.stringify(Array.from(els).filter(el => el.offsetParent !== null).map(el => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName,
          type: el.type || '',
          role: el.getAttribute('role') || '',
          checked: el.checked ?? el.getAttribute('aria-checked') ?? '',
          text: el.textContent?.trim().substring(0, 50) || '',
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        };
      }));
    `);
    console.log("\nAll interactive elements:", r);
  }

  if (!nextInfo.disabled) {
    await clickAt(send, nextInfo.x, nextInfo.y);
    console.log("Clicked Next!");
    await sleep(5000);
    r = await eval_(`return window.location.href`);
    console.log("\nNew URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nNew Page:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
