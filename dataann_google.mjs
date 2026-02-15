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
  let { ws, send, eval_ } = await connectToPage("dataannotation");

  // Click "Continue with Google"
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.includes('Continue with Google') && el.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Google button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    await sleep(6000);

    // Check tabs for Google auth
    const tabs = await (await fetch(CDP_HTTP + "/json")).json();
    console.log("\nTabs:");
    tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
    if (googleTab) {
      ws.close(); await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("accounts.google.com"));

      r = await eval_(`return document.body.innerText.substring(0, 1000)`);
      console.log("\nGoogle page:", r);

      // Click on bimopsstudio account
      r = await eval_(`
        const item = Array.from(document.querySelectorAll('li'))
          .find(el => el.textContent.includes('bimopsstudio'));
        if (item) {
          const rect = item.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return 'not found';
      `);
      console.log("\nBimops account:", r);

      if (r !== 'not found') {
        const aPos = JSON.parse(r);
        await clickAt(send, aPos.x, aPos.y);
        await sleep(8000);

        ws.close(); await sleep(1000);
        const tabs2 = await (await fetch(CDP_HTTP + "/json")).json();
        console.log("\nTabs after auth:");
        tabs2.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

        // Check DataAnnotation page
        const daTab = tabs2.find(t => t.type === "page" && t.url.includes("dataannotation"));
        if (daTab) {
          ({ ws, send, eval_ } = await connectToPage("dataannotation"));
          r = await eval_(`return window.location.href`);
          console.log("\nDataAnnotation URL:", r);
          r = await eval_(`return document.body.innerText.substring(0, 4000)`);
          console.log("\nPage:", r);
          ws.close();
        }
      }
    }
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
