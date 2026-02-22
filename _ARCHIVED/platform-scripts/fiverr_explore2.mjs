// Explore Fiverr seller menus - page already refreshed
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

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 300)
    });
  `);
  let state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Error?", state.isError);
  console.log("Body:", state.body.substring(0, 150));

  if (state.isError) {
    console.log("Still blocked! Exiting.");
    ws.close();
    return;
  }

  // Get ALL nav items in top bar
  console.log("\n=== Top Nav Items ===");
  r = await eval_(`
    const items = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y < 55 && rect.y > 0 && rect.height < 50 && rect.width > 20 && rect.width < 300;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width)
      }))
      .filter(l => l.text.length > 2 && l.text.length < 30);
    // Deduplicate by position
    const seen = new Set();
    return JSON.stringify(items.filter(i => {
      const key = Math.round(i.x/20) + ',' + Math.round(i.y/10);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }));
  `);
  console.log("Nav items:", r);

  // Hover over "My Business" to reveal dropdown
  console.log("\n=== Hovering My Business ===");
  r = await eval_(`
    const el = Array.from(document.querySelectorAll('*'))
      .find(e => e.textContent.trim() === 'My Business' && e.getBoundingClientRect().y < 55 && e.getBoundingClientRect().y > 0);
    if (el) {
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("My Business:", r);
  const mb = JSON.parse(r);

  if (!mb.error) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: mb.x, y: mb.y });
    await sleep(1500);

    // Check for ANY new elements that appeared
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('a'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 40 && rect.y < 500;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          href: (el.href || '').substring(0, 100),
          y: Math.round(el.getBoundingClientRect().y),
          x: Math.round(el.getBoundingClientRect().x)
        }))
        .filter(l => l.text.length > 0 && l.y < 400);
      return JSON.stringify(items.slice(0, 25));
    `);
    console.log("Dropdown links:", r);

    // Also click it
    await clickAt(send, mb.x, mb.y);
    await sleep(1500);

    r = await eval_(`
      const items = Array.from(document.querySelectorAll('a'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 40 && rect.y < 500;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          href: (el.href || '').substring(0, 100),
          y: Math.round(el.getBoundingClientRect().y)
        }))
        .filter(l => l.text.length > 0 && l.y < 400);
      return JSON.stringify(items.slice(0, 25));
    `);
    console.log("After click links:", r);
  }

  // Hover over "Growth & Marketing"
  console.log("\n=== Hovering Growth & Marketing ===");
  r = await eval_(`
    const el = Array.from(document.querySelectorAll('*'))
      .find(e => e.textContent.trim() === 'Growth & Marketing' && e.getBoundingClientRect().y < 55 && e.getBoundingClientRect().y > 0);
    if (el) {
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Growth:", r);
  const gm = JSON.parse(r);

  if (!gm.error) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: gm.x, y: gm.y });
    await sleep(1500);

    r = await eval_(`
      const items = Array.from(document.querySelectorAll('a'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 40 && rect.y < 500;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          href: (el.href || '').substring(0, 100),
          y: Math.round(el.getBoundingClientRect().y)
        }))
        .filter(l => l.text.length > 0 && l.y < 400);
      return JSON.stringify(items.slice(0, 25));
    `);
    console.log("Dropdown links:", r);
  }

  // Search page for "brief" or "request" text anywhere
  console.log("\n=== Searching entire page for brief/request ===");
  r = await eval_(`
    const html = document.documentElement.innerHTML;
    const matches = [];
    const terms = ['brief', 'request', 'matching', 'offer', 'proposal'];
    for (const term of terms) {
      const idx = html.toLowerCase().indexOf(term);
      if (idx !== -1) {
        matches.push({ term, context: html.substring(Math.max(0, idx-30), idx+50) });
      }
    }
    return JSON.stringify(matches);
  `);
  console.log("HTML search:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
