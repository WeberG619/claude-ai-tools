// Open inbox conversation and find availability in account settings
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

  // Go to inbox
  console.log("=== Going to Inbox ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/inbox'`);
  await sleep(5000);

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch')
    });
  `);
  let state = JSON.parse(r);
  console.log("URL:", state.url, "Error:", state.isError);

  if (!state.isError) {
    // Find all clickable conversation items
    r = await eval_(`
      // Look for conversation list items
      const items = Array.from(document.querySelectorAll('li, a, div[role="button"], [class*="conversation"], [class*="thread"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null &&
            el.textContent?.includes('Jamie') &&
            rect.width > 100 && rect.height > 20 && rect.height < 150;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 80),
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 80),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          w: Math.round(el.getBoundingClientRect().width),
          h: Math.round(el.getBoundingClientRect().height)
        }));
      return JSON.stringify(items);
    `);
    console.log("Conversation items:", r);
    const items = JSON.parse(r);

    // Click the most specific one (smallest bounding box that contains "Jamie")
    const best = items.sort((a, b) => (a.w * a.h) - (b.w * b.h))[0];
    if (best) {
      console.log(`Clicking at (${best.x}, ${best.y}) - ${best.tag} ${best.w}x${best.h}`);
      await clickAt(send, best.x, best.y);
      await sleep(3000);

      // Read the conversation
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          body: (document.body?.innerText || '').substring(0, 3000)
        });
      `);
      const conv = JSON.parse(r);
      console.log("\nConversation page:", conv.body);
    }
  }

  // Now navigate to account settings for availability
  console.log("\n=== Account Settings ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/account-settings'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 3000)
    });
  `);
  state = JSON.parse(r);

  if (state.isError) {
    console.log("Bot detection on account settings. Trying alternative...");
    // Try the seller levels page which might have availability
    await eval_(`window.location.href = 'https://www.fiverr.com/seller/levels'`);
    await sleep(5000);
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        isError: (document.body?.innerText || '').includes('human touch'),
        body: (document.body?.innerText || '').substring(0, 2000)
      });
    `);
    state = JSON.parse(r);
  }

  console.log("URL:", state.url);
  if (!state.isError) {
    console.log("Body:", state.body);

    // Look for availability/online toggles
    r = await eval_(`
      const toggles = Array.from(document.querySelectorAll('[role="switch"], input[type="checkbox"], [class*="toggle"], [class*="avail"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          checked: el.checked ?? el.getAttribute('aria-checked'),
          nearText: el.closest('div, label, section')?.textContent?.trim()?.substring(0, 100) || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(toggles);
    `);
    console.log("\nToggles:", r);
  } else {
    console.log("Still blocked by bot detection");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
