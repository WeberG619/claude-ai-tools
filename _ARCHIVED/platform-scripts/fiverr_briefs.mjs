// Find and navigate to Fiverr Briefs/Buyer Requests
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

  // First move mouse away, then hover Growth & Marketing properly
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 600, y: 400 });
  await sleep(500);

  // Hover Growth & Marketing
  console.log("=== Growth & Marketing dropdown ===");
  let r = await eval_(`
    const el = Array.from(document.querySelectorAll('li, a'))
      .find(e => e.textContent.trim() === 'Growth & Marketing' && e.getBoundingClientRect().y < 60);
    if (el) {
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const gm = JSON.parse(r);
  console.log("Found at:", r);

  if (!gm.error) {
    // Move away first
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 100, y: 300 });
    await sleep(300);
    // Now hover
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: gm.x, y: gm.y });
    await sleep(2000);

    r = await eval_(`
      // Get all visible links below the nav
      const items = Array.from(document.querySelectorAll('a'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 50 && rect.y < 350 && rect.x > 350;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 60),
          href: el.href || '',
          y: Math.round(el.getBoundingClientRect().y),
          x: Math.round(el.getBoundingClientRect().x)
        }))
        .filter(l => l.text.length > 0);
      return JSON.stringify(items);
    `);
    console.log("Dropdown:", r);
  }

  // Try clicking Growth & Marketing to navigate
  console.log("\n=== Clicking Growth & Marketing ===");
  if (!gm.error) {
    await clickAt(send, gm.x, gm.y);
    await sleep(4000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 1500)
      });
    `);
    const page = JSON.parse(r);
    console.log("URL:", page.url);
    console.log("Body:", page.body);
  }

  // Search for brief-related links in the page HTML
  console.log("\n=== Looking for Briefs access ===");
  r = await eval_(`
    // Search for any brief/request related href
    const allAnchors = Array.from(document.querySelectorAll('a'));
    const briefLinks = allAnchors.filter(a =>
      (a.href || '').toLowerCase().includes('brief') ||
      (a.href || '').toLowerCase().includes('buyer_request') ||
      (a.href || '').toLowerCase().includes('matching') ||
      a.textContent.toLowerCase().includes('brief') ||
      a.textContent.toLowerCase().includes('buyer request')
    ).map(a => ({
      text: a.textContent.trim().substring(0, 60),
      href: a.href,
      visible: a.offsetParent !== null
    }));
    return JSON.stringify(briefLinks);
  `);
  console.log("Brief links found:", r);

  // Check feature flags in the page
  r = await eval_(`
    const scripts = Array.from(document.querySelectorAll('script'));
    for (const s of scripts) {
      const text = s.textContent || '';
      if (text.includes('brief') || text.includes('Brief')) {
        const idx = text.toLowerCase().indexOf('brief');
        return text.substring(Math.max(0, idx-100), idx+200);
      }
    }
    return 'no brief in scripts';
  `);
  console.log("\nBrief in scripts:", r);

  // Check if there's a "Briefs" or "Matching" menu under any nav
  r = await eval_(`
    // Check ALL links on page
    const allLinks = Array.from(document.querySelectorAll('a'))
      .map(a => ({ text: a.textContent.trim().substring(0, 50), href: (a.href || '').substring(0, 100) }))
      .filter(l => l.text.length > 0);
    return JSON.stringify(allLinks.slice(0, 50));
  `);
  console.log("\nAll links:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
