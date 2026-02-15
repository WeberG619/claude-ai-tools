// Navigate to manage gigs and click "Create a New Gig"
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) {
    console.log("Available tabs:", tabs.map(t => t.url.substring(0, 80)));
    throw new Error(`Tab with "${urlMatch}" not found`);
  }
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
  // Connect to the Fiverr tab
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected to Fiverr tab");

  // Navigate to manage gigs
  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs" });
  await sleep(5000);

  // Reconnect after navigation
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 1500)
    });
  `);
  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Body:", state.body.substring(0, 800));

  // Find the "Create a New Gig" link
  r = await eval_(`
    const createBtn = Array.from(document.querySelectorAll('a, button'))
      .find(el => el.textContent.trim().includes('Create a New Gig') || el.textContent.trim().includes('Create New Gig'));
    if (createBtn) {
      return JSON.stringify({
        text: createBtn.textContent.trim().substring(0, 30),
        href: createBtn.href || '',
        tag: createBtn.tagName
      });
    }
    return JSON.stringify({ error: 'no create button' });
  `);
  console.log("Create button:", r);
  const createBtn = JSON.parse(r);

  if (createBtn.href) {
    console.log("Navigating to:", createBtn.href);
    await send("Page.navigate", { url: createBtn.href });
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: (document.body?.innerText || '').substring(200, 1000)
      });
    `);
    console.log("New gig page:", r);
  } else if (!createBtn.error) {
    // Click it via JS
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('a, button'))
        .find(el => el.textContent.trim().includes('Create a New Gig'));
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    `);
    console.log("JS click:", r);
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`return location.href`);
    console.log("After click URL:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
