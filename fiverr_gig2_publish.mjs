// Click Publish Gig button
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Find the Publish Gig button
  let r = await eval_(`
    const publishBtn = Array.from(document.querySelectorAll('button, a'))
      .find(el => {
        const text = el.textContent.trim();
        return (text === 'Publish Gig' || text === 'Publish') && el.offsetParent !== null;
      });
    if (publishBtn) {
      publishBtn.scrollIntoView({ block: 'center' });
      const rect = publishBtn.getBoundingClientRect();
      return JSON.stringify({
        text: publishBtn.textContent.trim(),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        tag: publishBtn.tagName
      });
    }
    return JSON.stringify({ error: 'no publish button' });
  `);
  console.log("Publish button:", r);
  const pubBtn = JSON.parse(r);

  if (!pubBtn.error) {
    await sleep(500);
    console.log(`Clicking "${pubBtn.text}" at (${pubBtn.x}, ${pubBtn.y})`);
    await clickAt(send, pubBtn.x, pubBtn.y);
    await sleep(8000);

    // Check result
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 1000)
      });
    `);
    const result = JSON.parse(r);
    console.log("\nURL:", result.url);
    console.log("Body:", result.body.substring(0, 500));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
