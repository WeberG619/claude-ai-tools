// Check all gig status tabs for hidden gigs
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Find all status tabs with their counts
  let r = await eval_(`
    const tabLinks = Array.from(document.querySelectorAll('a, [role="tab"]'))
      .filter(el => {
        const t = el.textContent.trim().toUpperCase();
        return (t.includes('ACTIVE') || t.includes('PENDING') || t.includes('DRAFT') ||
                t.includes('DENIED') || t.includes('PAUSED') || t.includes('REQUIRES'));
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        href: el.href || '',
        class: (el.className || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(tabLinks);
  `);
  console.log("Status tabs:", r);
  const statusTabs = JSON.parse(r);

  // Click each non-active tab to check for hidden gigs
  const tabsToCheck = ['PENDING', 'REQUIRES', 'DRAFT', 'DENIED', 'PAUSED'];
  for (const tabName of tabsToCheck) {
    const tab = statusTabs.find(t => t.text.toUpperCase().includes(tabName));
    if (!tab) continue;

    console.log(`\n=== Checking ${tabName} ===`);
    await clickAt(send, tab.x, tab.y);
    await sleep(2000);

    r = await eval_(`
      const gigs = Array.from(document.querySelectorAll('tr, [class*="gig-card"], [class*="gig-row"]'))
        .filter(el => {
          const text = el.textContent.trim();
          return text.length > 20 && text.length < 500
            && (el.querySelector('a[href*="manage_gigs"]') || text.includes('Edit'));
        })
        .map(el => el.textContent.trim().substring(0, 120));
      const noGigs = document.body.innerText.includes('No Gigs') || document.body.innerText.includes('no gigs');
      return JSON.stringify({ gigs, noGigs, bodySnip: document.body.innerText.substring(0, 200) });
    `);
    console.log(r);
  }

  // Go back to ACTIVE to see all gigs clearly
  console.log("\n=== ACTIVE GIGS ===");
  const activeTab = statusTabs.find(t => t.text.toUpperCase().includes('ACTIVE'));
  if (activeTab) {
    await clickAt(send, activeTab.x, activeTab.y);
    await sleep(2000);
  }

  r = await eval_(`
    const rows = Array.from(document.querySelectorAll('tr'))
      .filter(el => el.querySelector('a[href*="manage_gigs"]'))
      .map(el => {
        const link = el.querySelector('a[href*="manage_gigs"]');
        return {
          title: link?.textContent?.trim()?.substring(0, 80) || '',
          href: link?.href || '',
          editHref: el.querySelector('a[href*="edit"]')?.href || ''
        };
      });
    return JSON.stringify(rows);
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
