// Check Fiverr dashboard for buyer requests/briefs and next actions
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

  // Navigate to seller dashboard
  console.log("=== Navigating to Seller Dashboard ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/seller_dashboard'`);
  await sleep(5000);

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 3000)
    });
  `);
  const dash = JSON.parse(r);
  console.log("URL:", dash.url);
  console.log("Dashboard:", dash.bodyPreview);

  // Look for navigation links - especially Buyer Requests / Briefs
  console.log("\n=== Navigation Links ===");
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'))
      .filter(a => a.offsetParent !== null && a.textContent.trim().length > 0)
      .map(a => ({
        text: a.textContent.trim().substring(0, 60),
        href: a.href || '',
        y: Math.round(a.getBoundingClientRect().y)
      }))
      .filter(l =>
        l.text.toLowerCase().includes('request') ||
        l.text.toLowerCase().includes('brief') ||
        l.text.toLowerCase().includes('buyer') ||
        l.text.toLowerCase().includes('gig') ||
        l.text.toLowerCase().includes('order') ||
        l.text.toLowerCase().includes('inbox') ||
        l.text.toLowerCase().includes('promote') ||
        l.text.toLowerCase().includes('analytics') ||
        l.text.toLowerCase().includes('growth') ||
        l.text.toLowerCase().includes('marketing') ||
        l.href.includes('buyer_request') ||
        l.href.includes('briefs') ||
        l.href.includes('matching')
      );
    return JSON.stringify(links);
  `);
  console.log("Relevant links:", r);

  // Now check for Briefs/Buyer Requests page
  console.log("\n=== Checking Briefs ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/briefs'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 3000)
    });
  `);
  const briefs = JSON.parse(r);
  console.log("URL:", briefs.url);
  console.log("Briefs page:", briefs.bodyPreview);

  // Also check matching/requests
  console.log("\n=== Checking Matching Briefs ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs'`);
  await sleep(4000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  const gigs = JSON.parse(r);
  console.log("URL:", gigs.url);
  console.log("Gigs page:", gigs.bodyPreview);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
