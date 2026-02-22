// Edit Fiverr Gig #1: Resume -> MCP Server Development
// Navigate to edit page and analyze/fill the form
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

  // Navigate to the edit page for gig #1 (resume gig)
  const editUrl = "https://www.fiverr.com/users/weberg619/manage_gigs/write-a-professional-resume-cv-and-cover-letter-that-gets-interviews/edit";
  console.log("Navigating to edit page...");
  await eval_(`window.location.href = "${editUrl}"`);
  await sleep(5000);

  const url = await eval_(`window.location.href`);
  console.log("Current URL:", url);

  // Analyze edit form structure
  const analysis = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.title,
      steps: Array.from(document.querySelectorAll('[class*="step"], [class*="tab"], nav a, [class*="nav"] a')).map(s => s.textContent.trim().substring(0, 30)).filter(s => s.length > 0).slice(0, 10),
      inputs: Array.from(document.querySelectorAll('input:not([type=hidden]), textarea, select')).map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        value: (el.value || '').substring(0, 80),
        placeholder: (el.placeholder || '').substring(0, 60),
        ariaLabel: (el.getAttribute('aria-label') || '').substring(0, 40)
      })).slice(0, 25),
      labels: Array.from(document.querySelectorAll('label')).map(l => ({
        text: l.textContent.trim().substring(0, 50),
        for: l.getAttribute('for') || ''
      })).filter(l => l.text.length > 0).slice(0, 20),
      selects: Array.from(document.querySelectorAll('select')).map(s => ({
        name: s.name,
        id: s.id,
        options: Array.from(s.options).map(o => o.textContent.trim().substring(0, 40)).slice(0, 10)
      })),
      bodyText: document.body?.innerText?.substring(0, 800) || ''
    })
  `);
  console.log("Edit page analysis:", analysis);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
