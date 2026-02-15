// List all gigs on the manage page
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Get full page text
  let r = await eval_(`return document.body.innerText`);
  console.log("=== PAGE TEXT ===");
  console.log(r.substring(0, 2000));

  // Find all gig rows/cards
  r = await eval_(`
    const rows = Array.from(document.querySelectorAll('tr, [class*="gig-card"], [class*="gig-row"], [class*="gig-item"]'))
      .filter(el => el.textContent.includes('write') || el.textContent.includes('proof') || el.textContent.includes('revit') || el.textContent.includes('bim'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        class: el.className.substring(0, 50)
      }));
    return JSON.stringify(rows);
  `);
  console.log("\n=== GIG ROWS ===", r);

  // Check tab counts
  r = await eval_(`
    const tabs = Array.from(document.querySelectorAll('[class*="tab"], li'))
      .filter(el => {
        const t = el.textContent.trim();
        return (t.includes('ACTIVE') || t.includes('DRAFT') || t.includes('PENDING') || t.includes('DENIED') || t.includes('PAUSED'))
          && t.length < 30;
      })
      .map(el => el.textContent.trim());
    return JSON.stringify(tabs);
  `);
  console.log("\n=== TABS ===", r);

  // Check for drafts specifically
  r = await eval_(`
    const draftTab = Array.from(document.querySelectorAll('a, button, [role="tab"]'))
      .find(el => el.textContent.trim().includes('DRAFT'));
    if (draftTab) {
      const rect = draftTab.getBoundingClientRect();
      return JSON.stringify({
        text: draftTab.textContent.trim(),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return JSON.stringify({ error: 'no draft tab' });
  `);
  console.log("\nDraft tab:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
