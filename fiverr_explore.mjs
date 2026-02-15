// Explore Fiverr seller menus - start from dashboard
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

  // Navigate to dashboard
  console.log("Going to dashboard...");
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/seller_dashboard'`);
  await sleep(7000);

  let r = await eval_(`
    const body = document.body?.innerText || '';
    return JSON.stringify({
      url: location.href,
      isError: body.includes('human touch'),
      preview: body.substring(0, 300)
    });
  `);
  let state = JSON.parse(r);
  console.log("State:", state.preview.substring(0, 100));

  if (state.isError) {
    console.log("Bot detection. Trying page refresh...");
    await eval_(`location.reload()`);
    await sleep(8000);
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        isError: (document.body?.innerText || '').includes('human touch'),
        preview: (document.body?.innerText || '').substring(0, 300)
      });
    `);
    state = JSON.parse(r);
    console.log("After reload:", state.preview.substring(0, 100));
  }

  if (state.isError) {
    console.log("\nStill blocked. Let me try clicking the Dashboard link in the nav.");
    // Click the Fiverr logo or dashboard link
    r = await eval_(`
      const dashLink = Array.from(document.querySelectorAll('a'))
        .find(a => a.href?.includes('seller_dashboard'));
      if (dashLink) {
        dashLink.click();
        return 'clicked dashboard link';
      }
      return 'no dashboard link';
    `);
    console.log(r);
    await sleep(5000);
  }

  // Now check the page
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 200)
    });
  `);
  state = JSON.parse(r);

  if (state.isError) {
    console.log("\n=== STILL BLOCKED - Bot detection active ===");
    console.log("The automated navigation triggered Fiverr's bot detection.");
    console.log("Weber needs to manually refresh the page in Chrome to clear it.");
    ws.close();
    return;
  }

  // Dashboard loaded - explore menus
  console.log("\n=== Dashboard Loaded ===");
  console.log(state.body);

  // Get ALL links on the page
  r = await eval_(`
    const allLinks = Array.from(document.querySelectorAll('a'))
      .filter(a => a.offsetParent !== null && a.getBoundingClientRect().y < 800)
      .map(a => ({
        text: a.textContent.trim().substring(0, 50),
        href: (a.href || '').substring(0, 80),
        x: Math.round(a.getBoundingClientRect().x + a.getBoundingClientRect().width/2),
        y: Math.round(a.getBoundingClientRect().y + a.getBoundingClientRect().height/2)
      }))
      .filter(l => l.text.length > 0);
    return JSON.stringify(allLinks);
  `);
  console.log("\nAll visible links:", r);

  // Hover over each top nav item to reveal dropdowns
  const navItems = ['Dashboard', 'My Business', 'Growth & Marketing', 'Analytics'];
  for (const item of navItems) {
    r = await eval_(`
      const el = Array.from(document.querySelectorAll('a, span, button, li'))
        .find(e => e.textContent.trim() === '${item}' && e.getBoundingClientRect().y < 60);
      if (el) {
        const rect = el.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const coords = JSON.parse(r);
    if (!coords.error) {
      console.log(`\n--- Hovering ${item} at (${coords.x}, ${coords.y}) ---`);
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: coords.x, y: coords.y });
      await sleep(1000);

      r = await eval_(`
        const dropItems = Array.from(document.querySelectorAll('[class*="dropdown"] a, [class*="menu"] a, [class*="submenu"] a, ul[class] a'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.y > 30 && rect.y < 500 && rect.width > 0;
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 50),
            href: (el.href || '').substring(0, 80)
          }))
          .filter(l => l.text.length > 1);
        return JSON.stringify(dropItems);
      `);
      console.log(`${item} dropdown:`, r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
