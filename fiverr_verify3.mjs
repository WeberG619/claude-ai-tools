// Fiverr identity verification - physical clicks via CDP
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check current page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("Current page:", r);
  const state = JSON.parse(r);

  // Find the "Outside of my primary job" option and get its coordinates
  console.log("\n=== Finding option to click ===");
  r = await eval_(`
    const el = Array.from(document.querySelectorAll('*'))
      .find(e => e.textContent?.trim() === 'Outside of my primary job or profession' && e.children.length === 0);
    if (el) {
      const card = el.closest('div[class]') || el.parentElement;
      const rect = card.getBoundingClientRect();
      return JSON.stringify({
        found: true,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        tag: card.tagName,
        class: (card.className?.toString() || '').substring(0, 80),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("Option:", r);
  const opt = JSON.parse(r);

  if (opt.found) {
    console.log(`Physical click on option at (${opt.x}, ${opt.y})`);
    await clickAt(send, opt.x, opt.y);
    await sleep(1000);

    // Check if it got selected (visual change)
    r = await eval_(`
      const el = Array.from(document.querySelectorAll('*'))
        .find(e => e.textContent?.trim() === 'Outside of my primary job or profession' && e.children.length === 0);
      if (el) {
        const card = el.closest('div[class]') || el.parentElement;
        return JSON.stringify({
          class: card.className?.toString() || '',
          parentClass: card.parentElement?.className?.toString()?.substring(0, 80) || '',
          ariaSelected: card.getAttribute('aria-selected'),
          ariaChecked: card.getAttribute('aria-checked'),
          dataset: JSON.stringify(card.dataset)
        });
      }
      return 'not found';
    `);
    console.log("After selection:", r);
  }

  // Now find and physically click Next button
  console.log("\n=== Clicking Next ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        disabled: btn.disabled,
        class: (btn.className?.toString() || '').substring(0, 80)
      });
    }
    return JSON.stringify({ error: 'no Next button' });
  `);
  console.log("Next button:", r);
  const nextBtn = JSON.parse(r);

  if (!nextBtn.error) {
    if (nextBtn.disabled) {
      console.log("Next button is DISABLED - need to select option first");
    } else {
      console.log(`Physical click on Next at (${nextBtn.x}, ${nextBtn.y})`);
      await clickAt(send, nextBtn.x, nextBtn.y);
      await sleep(6000);
    }
  }

  // Check what page we're on now
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  console.log("\n=== After Next ===");
  const after = JSON.parse(r);
  console.log("URL:", after.url);
  console.log("Body:", after.bodyPreview);

  // Check for form fields on new page
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map(el => ({
        tag: el.tagName,
        type: el.type,
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 50),
        value: (el.value || '').substring(0, 50),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    const btns = Array.from(document.querySelectorAll('button, a[href]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        tag: el.tagName,
        href: el.href || '',
        y: Math.round(el.getBoundingClientRect().y)
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify({ inputs, btns: btns.slice(0, 15) });
  `);
  console.log("\nForm elements:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
