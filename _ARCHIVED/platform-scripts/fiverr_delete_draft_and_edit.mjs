// Step 1: Delete the draft gig
// Step 2: Transform gig #1 (resume -> MCP server)
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.type === "page");
  if (!tab) throw new Error("No Fiverr tab found");
  console.log(`Connected: ${tab.url}`);
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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) {
      console.error("JS Error:", JSON.stringify(r.exceptionDetails).substring(0, 300));
      return null;
    }
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, eval_ } = await connect();

  // ===== PART 1: Find and delete the draft gig =====
  console.log("\n=== Finding draft gig ===");
  await eval_(`window.location.href = "https://www.fiverr.com/users/weberg619/manage_gigs?current_filter=draft"`);
  await sleep(4000);

  const draftInfo = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.title,
      gigs: Array.from(document.querySelectorAll('a[href*="manage_gigs/"]')).map(a => ({
        text: a.textContent.trim().substring(0, 60),
        href: a.href
      })).filter(a => a.href.includes('/edit') || a.href.includes('/delete')),
      deleteButtons: Array.from(document.querySelectorAll('a[href*="delete"], button')).map(el => ({
        text: el.textContent.trim().substring(0, 40),
        href: el.href || '',
        tag: el.tagName
      })).filter(el => el.text.toLowerCase().includes('delete') || el.href.includes('delete')),
      allActions: Array.from(document.querySelectorAll('.actions a, [class*="action"] a, td a')).map(a => ({
        text: a.textContent.trim().substring(0, 40),
        href: a.href
      })).slice(0, 10),
      bodySnippet: document.body?.innerText?.substring(0, 500)
    })
  `);
  console.log("Draft page:", draftInfo);

  // Look for any delete option or the draft gig details
  const draftActions = await eval_(`
    JSON.stringify({
      forms: Array.from(document.querySelectorAll('form')).map(f => ({
        action: f.action,
        method: f.method,
        inputs: Array.from(f.querySelectorAll('input')).map(i => ({ name: i.name, value: i.value?.substring(0, 40), type: i.type }))
      })).filter(f => f.action.includes('delete') || f.action.includes('gig')).slice(0, 5),
      links: Array.from(document.querySelectorAll('a')).map(a => ({
        text: a.textContent.trim().substring(0, 40),
        href: a.href,
        class: a.className.substring(0, 40)
      })).filter(a => a.href.includes('delete') || a.text.toLowerCase().includes('delete') || a.href.includes('manage_gigs/')).slice(0, 15)
    })
  `);
  console.log("Draft actions:", draftActions);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
