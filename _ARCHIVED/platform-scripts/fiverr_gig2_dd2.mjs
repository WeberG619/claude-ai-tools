// Broad search for delivery time and revision components
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Get the full page text to understand current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 3000)
    });
  `);
  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Body:", state.body.substring(0, 2000));

  // Scroll down to see the pricing table
  await eval_(`window.scrollTo(0, 300)`);
  await sleep(500);

  // Find ALL elements containing "Delivery" text
  r = await eval_(`
    const deliveryEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return text.includes('Delivery') && el.children.length === 0 && el.offsetParent !== null;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(deliveryEls);
  `);
  console.log("\nAll 'Delivery' text elements:", r);

  // Find ALL elements containing "Select" text
  r = await eval_(`
    const selectEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return text === 'Select' && el.children.length === 0 && el.offsetParent !== null;
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(selectEls);
  `);
  console.log("\n'Select' text elements:", r);

  // Try the most direct approach - find the delivery time custom select component
  r = await eval_(`
    // Search for elements with "Delivery Time" as placeholder-like text
    const dtElements = Array.from(document.querySelectorAll('[class*="select"], [class*="dropdown"], [class*="picker"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 500)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
    return JSON.stringify(dtElements);
  `);
  console.log("\nSelect/dropdown/picker elements:", r);

  // Click the first "Delivery Time" cell text to see if it opens a dropdown
  const deliveryEls = JSON.parse(await eval_(`
    const els = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.trim() === 'Delivery Time' && el.children.length === 0 && el.offsetParent !== null && el.getBoundingClientRect().x > 400)
      .map(el => ({
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        parentTag: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 60)
      }));
    return JSON.stringify(els);
  `));

  if (deliveryEls.length > 0) {
    const first = deliveryEls[0];
    console.log(`\nClicking first Delivery Time cell at (${first.x}, ${first.y})`);
    console.log(`Parent: ${first.parentTag} class="${first.parentClass}"`);

    // Click the parent element (which is likely the dropdown trigger)
    await clickAt(send, first.x, first.y);
    await sleep(1500);

    // Capture the DOM state after click - look for menus/popups near the click position
    r = await eval_(`
      const clickY = ${first.y};
      const clickX = ${first.x};

      // Check if the parent element expanded
      const parent = document.elementFromPoint(clickX, clickY)?.parentElement;
      const parentRect = parent?.getBoundingClientRect();

      // Look for new visible elements with class containing "option" near the click area
      const newOptions = Array.from(document.querySelectorAll('[class*="option"], [class*="item"], [role="option"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > clickY - 20 && rect.y < clickY + 300;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));

      // Also check for aria-expanded
      const expanded = document.querySelector('[aria-expanded="true"]');

      return JSON.stringify({
        parentHeight: parentRect ? Math.round(parentRect.height) : 0,
        options: newOptions.slice(0, 15),
        hasExpanded: !!expanded,
        expandedText: expanded?.textContent?.trim()?.substring(0, 40) || ''
      });
    `);
    console.log("After click:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
