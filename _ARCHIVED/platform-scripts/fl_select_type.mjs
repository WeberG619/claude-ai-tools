// Click the FL-CARD for freelancing on Freelancer.com Angular app
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");

  // Use CDP Input.dispatchMouseEvent to simulate a real click
  // First, get the position of the "Earn money freelancing" card
  console.log("Getting card position...");
  let r = await eval_(`
    const card = document.querySelector('fl-card.RadioCard.CardClickable');
    if (!card) return null;
    const rect = card.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height });
  `);
  console.log("  Card rect:", r);

  if (r) {
    const pos = JSON.parse(r);
    // Dispatch real mouse events via CDP
    console.log("  Dispatching mouse click at", pos.x, pos.y);
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1
    });
    await sleep(100);
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1
    });
    await sleep(2000);

    // Check if card is now selected
    r = await eval_(`
      const card = document.querySelector('fl-card.RadioCard.CardClickable');
      const allCards = Array.from(document.querySelectorAll('fl-card'));
      return JSON.stringify({
        cardClasses: allCards.map(c => c.className),
        selected: allCards.map(c => ({
          text: c.textContent.trim().substring(0, 30),
          hasSelected: c.className.includes('Selected') || c.className.includes('selected') || c.className.includes('active'),
          classes: c.className
        }))
      }, null, 2);
    `);
    console.log("  Card state:", r);
  }

  // Look for hidden button or next action
  console.log("\nLooking for Next/Continue button...");
  r = await eval_(`
    // Get ALL elements including shadow DOM
    const allEls = Array.from(document.querySelectorAll('*'));
    const btns = allEls.filter(el => {
      const text = el.textContent?.trim() || '';
      return (text === 'Next' || text === 'Continue' || text === 'Get Started' || text === 'Start') &&
             el.tagName !== 'HTML' && el.tagName !== 'BODY';
    });
    return JSON.stringify(btns.map(b => ({
      tag: b.tagName, text: b.textContent.trim().substring(0, 30),
      class: b.className?.toString()?.substring(0, 80) || '',
      display: window.getComputedStyle(b).display,
      visibility: window.getComputedStyle(b).visibility,
      opacity: window.getComputedStyle(b).opacity,
      disabled: b.disabled
    })));
  `);
  console.log("  Buttons:", r);

  // Maybe the card click IS the next step - try clicking directly on Angular event
  console.log("\nTrying Angular approach...");
  r = await eval_(`
    // Try dispatching click event with all the right properties
    const card = Array.from(document.querySelectorAll('fl-card')).find(c => c.textContent.includes('Earn money'));
    if (!card) return 'card not found';

    // Create and dispatch a proper MouseEvent
    const event = new MouseEvent('click', {
      view: window, bubbles: true, cancelable: true, clientX: 100, clientY: 200
    });
    card.dispatchEvent(event);

    // Also try the inner clickable div
    const inner = card.querySelector('.CardClickable, .CardContainer, .CardBody');
    if (inner) {
      inner.dispatchEvent(new MouseEvent('click', { view: window, bubbles: true, cancelable: true }));
    }

    return 'dispatched click events';
  `);
  console.log("  ", r);
  await sleep(3000);

  // Final check
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 500),
      allBtns: Array.from(document.querySelectorAll('button, fl-button, [role="button"]'))
        .map(b => ({ text: b.textContent.trim().substring(0, 40), visible: b.offsetParent !== null, disabled: b.disabled, class: (b.className||'').toString().substring(0,50) }))
    }, null, 2);
  `);
  console.log("\nFinal state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
