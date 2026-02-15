// Click "Create a new Gig" link via CDP (not JS navigation)
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
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected");

  // Make sure we're on the gigs page
  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  if (!r.includes("manage_gigs")) {
    await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs'`);
    await sleep(5000);
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("fiverr.com"));
  }

  // Find "Create a new Gig" and CDP-click it
  r = await eval_(`
    const link = Array.from(document.querySelectorAll('a'))
      .find(el => el.textContent.trim().includes('Create a new Gig'));
    if (link) {
      link.scrollIntoView({ block: 'center' });
      const rect = link.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), href: link.href });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Create link:", r);
  const link = JSON.parse(r);

  if (!link.error) {
    await sleep(500);
    console.log(`CDP clicking at (${link.x}, ${link.y})`);
    await clickAt(send, link.x, link.y);
    await sleep(8000);

    // Reconnect
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("fiverr.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        title: document.title,
        body: document.body.innerText.substring(0, 400)
      });
    `);
    console.log("After click:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
