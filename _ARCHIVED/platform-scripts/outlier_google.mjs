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
      expression: `(async () => { ${expr} })()`,
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
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Click "Continue with Google" button at (626, 566)
  console.log("Clicking Continue with Google...");
  await clickAt(send, 626, 566);
  await sleep(8000);

  // Check all tabs for Google auth popup
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  console.log("\nOpen tabs after Google click:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

  // Try to connect to Google auth page
  const googleTab = tabs.find(t => t.type === "page" && (t.url.includes("accounts.google.com") || t.url.includes("auth")));
  if (googleTab) {
    ws.close(); await sleep(500);
    const ws2 = new WebSocket(googleTab.webSocketDebuggerUrl);
    await new Promise(r => ws2.addEventListener("open", r));
    let id2 = 1;
    const pending2 = new Map();
    ws2.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending2.has(m.id)) {
        const p = pending2.get(m.id);
        pending2.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const eval2 = async (expr) => {
      const i = id2++;
      const r = await new Promise((res, rej) => {
        pending2.set(i, { res, rej });
        ws2.send(JSON.stringify({ id: i, method: "Runtime.evaluate", params: {
          expression: `(async () => { ${expr} })()`,
          returnByValue: true, awaitPromise: true
        }}));
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    let r = await eval2(`return window.location.href`);
    console.log("\nGoogle auth URL:", r);

    r = await eval2(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nGoogle page:");
    console.log(r);

    ws2.close();
  } else {
    // Maybe it stayed on same page - check Outlier page state
    ws.close(); await sleep(500);
    const conn = await connectToPage("outlier");
    if (conn) {
      let r = await conn.eval_(`return window.location.href`);
      console.log("\nOutlier URL:", r);
      r = await conn.eval_(`return document.body.innerText.substring(0, 3000)`);
      console.log("\nOutlier page:", r);
      conn.ws.close();
    }
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
