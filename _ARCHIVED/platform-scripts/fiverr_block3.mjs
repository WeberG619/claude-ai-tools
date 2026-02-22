// Block scammer - click Actions button and find block/report
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

  // Take snapshot of all elements before clicking
  console.log("=== Snapshot before Actions click ===");
  let r = await eval_(`
    return document.querySelectorAll('*').length;
  `);
  const beforeCount = r;
  console.log("Element count:", beforeCount);

  // Click the "Actions" button at (918, 155)
  console.log("\nClicking Actions button...");
  await clickAt(send, 918, 155);
  await sleep(2000);

  // Check what NEW elements appeared
  r = await eval_(`
    // Get everything that's visible and could be a menu item
    const allVisible = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 &&
          rect.height < 50 && rect.width > 80 &&
          rect.y > 150 && rect.y < 500 &&
          style.display !== 'none' && style.visibility !== 'hidden' &&
          el.textContent?.trim()?.length > 0 && el.textContent?.trim()?.length < 40 &&
          el.children.length === 0;
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        parent: el.parentElement?.tagName + '.' + (el.parentElement?.className?.toString() || '').substring(0, 40)
      }));

    // Filter to things that look like menu items
    const menuLike = allVisible.filter(el =>
      el.x > 700 && el.y > 160 && el.y < 400
    );

    return JSON.stringify({ total: allVisible.length, menuLike });
  `);
  console.log("After Actions click:", r);

  // Also check the full DOM snapshot for any new visible containers
  r = await eval_(`
    const newCount = document.querySelectorAll('*').length;
    // Find elements that might be a dropdown/popover
    const containers = Array.from(document.querySelectorAll('div, ul'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 80 && rect.width < 300 &&
          rect.height > 40 && rect.height < 400 &&
          rect.y > 160 && rect.y < 400 &&
          rect.x > 600 &&
          style.display !== 'none' && style.visibility !== 'hidden' &&
          style.position === 'absolute' || style.position === 'fixed' ||
          el.style.zIndex > 0;
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 200),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height),
        zIndex: window.getComputedStyle(el).zIndex
      }));
    return JSON.stringify({ newCount, containers });
  `);
  console.log("Containers:", r);

  // Try clicking Actions again after closing
  await clickAt(send, 600, 500); // click away
  await sleep(500);

  // Try the three dots specifically - look for an SVG with 3 dots pattern
  console.log("\n=== Looking for three-dot menu via HTML ===");
  r = await eval_(`
    const html = document.documentElement.innerHTML;
    // Find elements near the Actions area
    const actionsBtn = document.querySelector('[aria-label="Actions"]');
    if (actionsBtn) {
      return JSON.stringify({
        tag: actionsBtn.tagName,
        parent: actionsBtn.parentElement?.outerHTML?.substring(0, 300),
        html: actionsBtn.outerHTML?.substring(0, 300),
        onclick: actionsBtn.onclick?.toString()?.substring(0, 100) || 'none'
      });
    }
    return 'no actions button';
  `);
  console.log("Actions button HTML:", r);

  // Try clicking it and immediately check
  console.log("\n=== Click Actions and check immediately ===");
  await clickAt(send, 918, 155);
  await sleep(500);

  r = await eval_(`
    // Check for any portal/overlay that might have rendered
    const portals = Array.from(document.querySelectorAll('[data-portal], [class*="portal"], [class*="Popover"], [class*="popover"], [class*="Tooltip"], [class*="floating"]'))
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 200),
        visible: el.offsetParent !== null,
        rect: el.getBoundingClientRect()
      }));

    // Also check body's last children (portals often append there)
    const lastChildren = Array.from(document.body.children)
      .slice(-5)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 200),
        visible: el.offsetParent !== null
      }));

    return JSON.stringify({ portals, lastChildren });
  `);
  console.log("Portals/last children:", r);

  // If we still can't find it, try the Fiverr API to block
  console.log("\n=== Attempting API block ===");
  r = await eval_(`
    return document.cookie.substring(0, 200);
  `);
  console.log("Cookies (first 200):", r);

  // Try fetching the block endpoint directly
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        const res = await fetch('https://www.fiverr.com/blocked_users/anna_39610ogm', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'include'
        });
        const text = await res.text();
        resolve(JSON.stringify({ status: res.status, body: text.substring(0, 300) }));
      } catch(e) {
        resolve(JSON.stringify({ error: e.message }));
      }
    });
  `);
  console.log("Block API response:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
