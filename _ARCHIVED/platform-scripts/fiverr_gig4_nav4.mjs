// Try creating gig #4 - check all tabs
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  // Check all tabs first
  let res = await fetch(`${CDP_HTTP}/json`);
  let tabs = await res.json();
  console.log("=== ALL TABS ===");
  for (const t of tabs) {
    if (t.type === "page") {
      console.log(`  ${t.title} | ${t.url.substring(0, 100)}`);
    }
  }

  // Connect to the manage_gigs page
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) { console.log("No manage_gigs tab"); return; }

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

  // Click the Create button
  const clickAt = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  };

  let r = await eval_(`
    const link = Array.from(document.querySelectorAll('a'))
      .find(el => el.textContent.trim().includes('Create a new Gig'));
    if (link) {
      link.scrollIntoView({ block: 'center' });
      const rect = link.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        href: link.href,
        target: link.target
      });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("\nCreate link:", r);
  const link = JSON.parse(r);

  if (!link.error) {
    console.log(`Clicking at (${link.x}, ${link.y}), target="${link.target}"`);
    await clickAt(link.x, link.y);
    await sleep(3000);

    // Check URL immediately
    r = await eval_(`return location.href`);
    console.log("URL after 3s:", r);

    // Wait more
    await sleep(5000);

    // Check all tabs again
    res = await fetch(`${CDP_HTTP}/json`);
    tabs = await res.json();
    console.log("\n=== ALL TABS AFTER CLICK ===");
    for (const t of tabs) {
      if (t.type === "page") {
        console.log(`  ${t.title} | ${t.url.substring(0, 100)}`);
      }
    }

    // Current URL
    r = await eval_(`return location.href`);
    console.log("\nCurrent URL:", r);

    // Check if there's a "new" tab now
    const newTab = tabs.find(t => t.type === "page" && t.url.includes("/new"));
    if (newTab) {
      console.log("\nFound new tab:", newTab.url);
    }

    // Check page body for any changes
    r = await eval_(`return document.body.innerText.substring(0, 300)`);
    console.log("\nBody:", r);

    // Maybe the notification is blocking - try to find it
    r = await eval_(`
      const notif = document.querySelector('[class*="notification"], [class*="alert"], [class*="toast"], [class*="flash"]');
      if (notif) {
        return JSON.stringify({
          text: notif.textContent.trim().substring(0, 100),
          class: notif.className.substring(0, 60)
        });
      }
      return 'no notification';
    `);
    console.log("\nNotification:", r);

    // Check if the "max 4 gigs" is actually a hard block
    r = await eval_(`
      const maxNotice = Array.from(document.querySelectorAll('*'))
        .find(el => el.textContent.includes('maximum of 4') && el.children.length < 3);
      if (maxNotice) {
        return JSON.stringify({
          tag: maxNotice.tagName,
          class: maxNotice.className.substring(0, 60),
          parentClass: maxNotice.parentElement?.className?.substring(0, 60) || ''
        });
      }
      return 'not found';
    `);
    console.log("Max notice element:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
