// Find and click "Create a New Gig" on manage gigs page
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab with "${urlMatch}" not found`);
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Find "CREATE A NEW GIG" button/link - it might be any element
  let r = await eval_(`
    const allElements = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        return (text === 'CREATE A NEW GIG' || text === 'Create a New Gig' || text === 'Create A New Gig')
          && el.offsetParent !== null
          && el.children.length === 0;  // leaf node only
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent.trim(),
        href: el.href || el.closest('a')?.href || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(allElements);
  `);
  console.log("CREATE buttons:", r);
  const buttons = JSON.parse(r);

  if (buttons.length > 0) {
    const btn = buttons[0];
    if (btn.href) {
      console.log("Navigating to:", btn.href);
      await send("Page.navigate", { url: btn.href });
    } else {
      console.log(`Clicking "${btn.text}" (${btn.tag}) at (${btn.x}, ${btn.y})`);
      await clickAt(send, btn.x, btn.y);
    }
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: (document.body?.innerText || '').substring(200, 1200)
      });
    `);
    const state = JSON.parse(r);
    console.log("URL:", state.url);
    console.log("Wizard:", state.wizard);
    console.log("Body:", state.body.substring(0, 600));
  } else {
    // Try direct URL
    console.log("No button found, trying direct URL...");
    await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs/new" });
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(200, 800)
      });
    `);
    console.log("Result:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
