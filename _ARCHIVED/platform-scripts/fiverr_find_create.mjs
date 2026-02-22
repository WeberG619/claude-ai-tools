// Find the "Create a New Gig" button/link on Fiverr
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com"));
  if (!tab) throw new Error("No Fiverr tab found");
  console.log(`Tab: ${tab.url}`);
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
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, eval_ } = await connect();

  // First navigate to manage_gigs
  await eval_(`window.location.href = "https://www.fiverr.com/users/weberg619/manage_gigs"`);
  await sleep(4000);

  console.log("Current URL:", await eval_(`window.location.href`));

  // Find all links and buttons with "create" or "new" or "gig" in text or href
  const result = await eval_(`
    JSON.stringify({
      links: Array.from(document.querySelectorAll('a')).filter(a => {
        const text = (a.textContent || '').toLowerCase();
        const href = (a.href || '').toLowerCase();
        return text.includes('create') || text.includes('new gig') || href.includes('create') || href.includes('new');
      }).map(a => ({ text: a.textContent.trim().substring(0, 60), href: a.href })),
      buttons: Array.from(document.querySelectorAll('button')).filter(b => {
        const text = (b.textContent || '').toLowerCase();
        return text.includes('create') || text.includes('new');
      }).map(b => ({ text: b.textContent.trim().substring(0, 60), class: b.className.substring(0, 60) })),
      allLinks: Array.from(document.querySelectorAll('a[href*="gig"]')).map(a => ({
        text: a.textContent.trim().substring(0, 60),
        href: a.href
      }))
    })
  `);

  console.log("Results:", result);
  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
