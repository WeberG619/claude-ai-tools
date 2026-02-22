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
  // Connect to Google account chooser
  let { ws, send, eval_ } = await connectToPage("accounts.google.com");

  // Click on the Weber Gouin / weber@bimopsstudio.com account
  let r = await eval_(`
    const accountEl = Array.from(document.querySelectorAll('[data-email], [data-identifier], li, div'))
      .find(el => el.textContent.includes('weber@bimopsstudio.com') || el.textContent.includes('Weber Gouin'));
    if (accountEl) {
      const rect = accountEl.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: accountEl.textContent.trim().substring(0, 60) });
    }
    return 'not found';
  `);
  console.log("Account element:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    console.log("Clicking account at:", pos.x, pos.y);
    await clickAt(send, pos.x, pos.y);
    await sleep(8000);

    // Check tabs
    const tabs = await (await fetch(CDP_HTTP + "/json")).json();
    console.log("\nTabs after clicking account:");
    tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    // Try to find Outlier page
    ws.close(); await sleep(1000);
    const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
    if (outlierTab) {
      const conn = await connectToPage("outlier");
      r = await conn.eval_(`return window.location.href`);
      console.log("\nOutlier URL:", r);

      r = await conn.eval_(`
        const body = document.body.innerText;
        return body.substring(0, 5000);
      `);
      console.log("\nOutlier page:");
      console.log(r);

      // Look for onboarding steps / form
      r = await conn.eval_(`
        const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({ tag: el.tagName, type: el.type, name: el.name, placeholder: el.placeholder, id: el.id }));
        const btns = Array.from(document.querySelectorAll('a, button'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
          .map(el => ({ text: el.textContent.trim(), href: el.href || '', tag: el.tagName }));
        return JSON.stringify({ inputs, buttons: btns }, null, 2);
      `);
      console.log("\nForm elements:", r);

      conn.ws.close();
    } else {
      // Maybe still on Google
      const gTab = tabs.find(t => t.type === "page" && t.url.includes("google.com"));
      if (gTab) {
        const conn = await connectToPage("google.com");
        r = await conn.eval_(`return document.body.innerText.substring(0, 2000)`);
        console.log("\nStill on Google:", r);
        conn.ws.close();
      }
    }
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
