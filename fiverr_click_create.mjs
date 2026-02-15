// Click "Create a new Gig" on Fiverr and analyze the resulting page
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

  // Make sure we're on manage_gigs
  console.log("Ensuring we're on manage_gigs...");
  await eval_(`
    if (!window.location.href.includes('manage_gigs')) {
      window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs';
    }
  `);
  await sleep(3000);

  // Click the "Create a new Gig" link
  console.log("Clicking 'Create a new Gig'...");
  const clickResult = await eval_(`
    (function() {
      const links = Array.from(document.querySelectorAll('a'));
      const createLink = links.find(a => a.textContent.trim().includes('Create a new Gig'));
      if (createLink) {
        createLink.click();
        return 'clicked: ' + createLink.href;
      }
      return 'not_found';
    })()
  `);
  console.log("Click result:", clickResult);

  // Wait for navigation
  await sleep(5000);

  // Check where we are now
  const url = await eval_(`window.location.href`);
  console.log("Current URL:", url);
  const title = await eval_(`document.title`);
  console.log("Page title:", title);

  // Analyze the new page
  const analysis = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.title,
      h1: document.querySelector('h1')?.textContent?.trim() || 'none',
      h2s: Array.from(document.querySelectorAll('h2,h3')).map(h => h.textContent.trim()).slice(0, 10),
      inputs: Array.from(document.querySelectorAll('input:not([type=hidden]), textarea, select')).map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 60),
        ariaLabel: el.getAttribute('aria-label') || ''
      })).slice(0, 20),
      buttons: Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent.trim().substring(0, 50),
        disabled: b.disabled
      })).filter(b => b.text.length > 0 && !b.text.includes('USD') && !b.text.includes('EUR')).slice(0, 10),
      labels: Array.from(document.querySelectorAll('label')).map(l => l.textContent.trim().substring(0, 50)).filter(l => l.length > 0).slice(0, 15),
      textContent: document.body?.innerText?.substring(0, 500) || ''
    })
  `);
  console.log("Page analysis:", analysis);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
